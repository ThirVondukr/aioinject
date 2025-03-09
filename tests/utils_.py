import asyncio
import contextlib
import functools
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import ParamSpec, TypeVar


T = TypeVar("T")
P = ParamSpec("P")


def dummy_decorator(func: Callable[P, T]) -> Callable[P, T]:
    @functools.wraps(func)
    def decorator(*args: P.args, **kwargs: P.kwargs) -> T:
        return func(*args, **kwargs)

    return decorator


async def maybe_await(value: Awaitable[T] | T) -> T:
    if asyncio.iscoroutine(value) or isinstance(value, Awaitable):
        return await value
    return value


@contextlib.asynccontextmanager
async def maybe_async_context(
    ctx: contextlib.AbstractAsyncContextManager[T]
    | contextlib.AbstractContextManager[T],
) -> AsyncIterator[T]:
    """Handle both synchronous and asynchronous context managers."""
    if isinstance(ctx, contextlib.AbstractAsyncContextManager):
        async with ctx as value:
            yield value
    else:
        with ctx as value:
            yield value
