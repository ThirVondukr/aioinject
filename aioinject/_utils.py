from __future__ import annotations

import collections.abc
import contextlib
import functools
import inspect
import sys
import typing
from collections.abc import Callable, Iterator
from contextlib import (
    AbstractAsyncContextManager,
    AbstractContextManager,
    AsyncExitStack,
    ExitStack,
)
from typing import Any, TypeVar

from aioinject.markers import Inject


_T = TypeVar("_T")
_F = TypeVar("_F", bound=Callable[..., Any])

sentinel = object()


def clear_wrapper(wrapper: _F) -> _F:
    inject_annotations = get_inject_annotations(wrapper)
    signature = inspect.signature(wrapper)
    new_params = tuple(
        p
        for p in signature.parameters.values()
        if p.name not in inject_annotations
    )
    wrapper.__signature__ = signature.replace(  # type: ignore[attr-defined]
        parameters=new_params,
    )
    for name in inject_annotations:
        del wrapper.__annotations__[name]
    return wrapper


def get_inject_annotations(
    function: Callable[..., Any],
) -> dict[str, Any]:
    with remove_annotation(function.__annotations__, "return"):
        return {
            name: annotation
            for name, annotation in typing.get_type_hints(
                function,
                include_extras=True,
            ).items()
            if any(
                isinstance(arg, Inject) or arg is Inject
                for arg in typing.get_args(annotation)
            )
        }


def is_context_manager_function(func: Callable[..., Any]) -> bool:
    while inner := getattr(func, "__wrapped__", None):
        func = inner
    return inspect.isgeneratorfunction(func) or inspect.isasyncgenfunction(
        func,
    )


async def enter_context_maybe(
    resolved: (
        _T | AbstractContextManager[_T] | AbstractAsyncContextManager[_T]
    ),
    stack: AsyncExitStack,
) -> _T:
    if isinstance(resolved, contextlib.AsyncContextDecorator):
        return await stack.enter_async_context(
            resolved,  # type: ignore[arg-type]
        )
    if isinstance(resolved, contextlib.ContextDecorator):
        return stack.enter_context(resolved)  # type: ignore[arg-type]

    return resolved  # type: ignore[return-value]


def enter_sync_context_maybe(
    resolved: _T | AbstractContextManager[_T],
    stack: ExitStack,
) -> _T:
    if isinstance(resolved, contextlib.ContextDecorator):
        return stack.enter_context(resolved)  # type: ignore[arg-type]
    return resolved  # type: ignore[return-value]


@contextlib.contextmanager
def remove_annotation(
    annotations: dict[str, Any],
    name: str,
) -> Iterator[None]:
    annotation = annotations.pop(name, sentinel)
    yield
    if annotation is not sentinel:
        annotations[name] = annotation


def _get_type_hints(
    obj: Any,
    context: dict[str, type[Any]] | None = None,
) -> dict[str, Any]:
    if not context:
        context = {}
    return typing.get_type_hints(obj, include_extras=True, localns=context)


def get_fn_ns(fn: Callable[..., Any]) -> dict[str, Any]:
    return getattr(sys.modules.get(fn.__module__, None), "__dict__", {})


def get_return_annotation(
    ret_annotation: str,
    context: dict[str, Any],
) -> type[Any]:
    return eval(ret_annotation, context)  # noqa: S307


@functools.cache
def is_iterable_generic_collection(type_: Any) -> bool:
    if not (origin := typing.get_origin(type_)):
        return False
    return collections.abc.Iterable in inspect.getmro(origin) or issubclass(
        origin, collections.abc.Iterable
    )
