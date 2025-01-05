from __future__ import annotations

import functools
import types
import typing as t
from types import GenericAlias
from typing import TYPE_CHECKING, Any, TypeGuard


if TYPE_CHECKING:
    from aioinject.providers import Dependency


def _is_generic_alias(type_: Any) -> TypeGuard[GenericAlias]:
    # we currently don't support tuple, list, dict, set, type
    return isinstance(
        type_,
        types.GenericAlias | t._GenericAlias,  # type: ignore[attr-defined] # noqa: SLF001
    ) and t.get_origin(type_) not in (tuple, list, dict, set, type)


def _get_orig_bases(type_: type) -> tuple[type, ...] | None:
    return getattr(type_, "__orig_bases__", None)


def _get_generic_arguments(type_: Any) -> list[t.TypeVar] | None:
    """
    Returns generic arguments of given class, e.g. Class[T] would return [~T]
    """
    if _is_generic_alias(type_):
        args = t.get_args(type_)
        return [arg for arg in args if isinstance(arg, t.TypeVar)]
    return None


@functools.lru_cache
def _get_generic_args_map(type_: type[object]) -> dict[str, type[object]]:
    if _is_generic_alias(type_):
        args = type_.__args__
        params: dict[str, Any] = {
            param.__name__: param
            for param in type_.__origin__.__parameters__  # type: ignore[attr-defined]
        }
        return dict(zip(params.keys(), args, strict=False))

    args_map = {}
    if orig_bases := _get_orig_bases(type_):
        # find the generic parent
        for base in orig_bases:
            if _is_generic_alias(base):
                args = base.__args__
                if params := {
                    param.__name__: param
                    for param in getattr(base.__origin__, "__parameters__", ())
                }:
                    args_map.update(
                        dict(zip(params, args, strict=True)),
                    )
    return args_map


@functools.lru_cache
def get_generic_parameter_map(
    provided_type: type[object],
    dependencies: tuple[Dependency[Any], ...],
) -> dict[str, type[object]]:
    args_map = _get_generic_args_map(provided_type)  # type: ignore[arg-type]
    result = {}
    for dependency in dependencies:
        if args_map and (
            generic_arguments := _get_generic_arguments(dependency.type_)
        ):
            # This is a generic type, we need to resolve the type arguments
            # and pass them to the provider.
            resolved_args = [
                args_map[arg.__name__] for arg in generic_arguments
            ]
            #  We can use `[]` when we drop support for 3.10
            result[dependency.name] = dependency.type_.__getitem__(
                *resolved_args
            )
    return result
