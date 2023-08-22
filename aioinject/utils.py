import contextlib
import inspect
import typing
from collections.abc import Awaitable, Iterator
from contextlib import (
    AbstractAsyncContextManager,
    AbstractContextManager,
    AsyncExitStack,
)
from typing import Any, TypeVar, cast

from aioinject.markers import Inject


_T = TypeVar("_T")
_F = TypeVar("_F", bound=typing.Callable[..., Any])

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
    function: typing.Callable[..., Any],
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


def enter_context_maybe(
    resolved: (
        _T | AbstractContextManager[_T] | AbstractAsyncContextManager[_T]
    ),
    stack: AsyncExitStack,
) -> _T | Awaitable[_T]:
    if isinstance(resolved, contextlib.ContextDecorator):
        return stack.enter_context(resolved)  # type: ignore[arg-type]

    if isinstance(resolved, contextlib.AsyncContextDecorator):
        return stack.enter_async_context(
            resolved,  # type: ignore[arg-type]
        )
    return resolved  # type: ignore[return-value]


async def await_maybe(value: _T | Awaitable[_T]) -> _T:
    if inspect.isawaitable(value):
        return await value
    return cast(_T, value)


@contextlib.contextmanager
def remove_annotation(
    annotations: dict[str, Any],
    name: str,
) -> Iterator[None]:
    annotation = annotations.pop(name, sentinel)
    yield
    if annotation is not sentinel:
        annotations[name] = annotation
