from __future__ import annotations

import functools
import inspect
from collections.abc import Sequence
from typing import Annotated, Any

from aioinject._types import T
from aioinject._utils import _get_type_hints
from aioinject.markers import Inject
from aioinject.providers import (
    Dependency,
    Object,
    Provider,
    Scoped,
    Singleton,
    Transient,
    _get_annotation_args,
    _guess_return_type,
    _typevar_map,
    collect_dependencies,
)

from ._abc import Extension, SupportsDependencyExtraction


def _get_dependencies(
    obj: type[Any],
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source, typevar_map = _typevar_map(obj)

    if inspect.isclass(source):
        source = source.__init__

    if isinstance(source, functools.partial):
        return {}

    type_hints = _get_type_hints(source, context=context)
    for key, value in type_hints.items():
        _, args = _get_annotation_args(value)
        for arg in args:
            if isinstance(arg, Inject):
                break
        else:
            type_hints[key] = Annotated[typevar_map.get(value, value), Inject]

    return type_hints


class BuiltinDependencyExtractor(SupportsDependencyExtraction):
    def extract_supports(self, provider: Provider[Any]) -> bool:
        return isinstance(provider, Transient | Scoped | Singleton)

    def extract_dependencies(
        self,
        provider: Provider[Any],
        context: dict[str, Any],
    ) -> tuple[Dependency[object], ...]:
        type_hints = _get_dependencies(provider.impl, context=context)
        if "return" in type_hints:
            del type_hints["return"]

        return tuple(
            collect_dependencies(type_hints, ctx=context),
        )

    def extract_type(
        self,
        provider: Provider[T],
    ) -> type[T]:
        return provider.type_ or _guess_return_type(provider.type_)


class ObjectDependencyExtractor(SupportsDependencyExtraction):
    def extract_supports(self, provider: Provider[Any]) -> bool:
        return isinstance(provider, Object)

    def extract_dependencies(
        self,
        provider: Provider[Any],  # noqa: ARG002
        context: dict[str, Any],  # noqa: ARG002
    ) -> tuple[Dependency[object], ...]:
        return ()

    def extract_type(
        self,
        provider: Provider[T],
    ) -> type[T]:
        return provider.type_


DEFAULT_EXTENSIONS: Sequence[Extension] = [
    ObjectDependencyExtractor(),
    BuiltinDependencyExtractor(),
]
