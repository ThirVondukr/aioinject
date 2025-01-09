from __future__ import annotations

import collections
import contextlib
import enum
import threading
import typing
from collections.abc import AsyncIterator, Iterator
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from types import TracebackType
from typing import TYPE_CHECKING, Any, Literal, TypeVar

import anyio

from aioinject._utils import enter_context_maybe, enter_sync_context_maybe
from aioinject.providers import DependencyLifetime


if TYPE_CHECKING:
    from typing_extensions import Self

    from aioinject.providers import Provider

T = TypeVar("T")


class NotInCache(enum.Enum):
    sentinel = enum.auto()


class InstanceStore:
    def __init__(
        self,
        exit_stack: contextlib.AsyncExitStack | None = None,
        sync_exit_stack: contextlib.ExitStack | None = None,
    ) -> None:
        self._cache: dict[Provider[Any], Any] = {}
        self._exit_stack = exit_stack or contextlib.AsyncExitStack()
        self._sync_exit_stack = sync_exit_stack or contextlib.ExitStack()

    def get(self, provider: Provider[T]) -> T | Literal[NotInCache.sentinel]:
        return self._cache.get(provider, NotInCache.sentinel)

    def add(self, provider: Provider[T], obj: T) -> None:
        if provider.lifetime is not DependencyLifetime.transient:
            self._cache[provider] = obj

    def lock(
        self,
        provider: Provider[Any],
    ) -> AbstractAsyncContextManager[bool]:
        return contextlib.nullcontext(
            provider not in self._cache
        )

    def sync_lock(
        self,
        provider: Provider[Any],
    ) -> AbstractContextManager[bool]:
        return contextlib.nullcontext(
            provider not in self._cache
        )

    @typing.overload
    async def enter_context(
        self,
        obj: AbstractAsyncContextManager[T] | AbstractContextManager[T],
    ) -> T: ...

    @typing.overload
    async def enter_context(self, obj: T) -> T: ...

    async def enter_context(
        self,
        obj: AbstractAsyncContextManager[T] | AbstractContextManager[T] | T,
    ) -> T:
        return await enter_context_maybe(obj, self._exit_stack)

    @typing.overload
    def enter_sync_context(self, obj: AbstractContextManager[T]) -> T: ...

    @typing.overload
    def enter_sync_context(self, obj: T) -> T: ...

    def enter_sync_context(
        self,
        obj: AbstractContextManager[T] | T,
    ) -> T:
        return enter_sync_context_maybe(obj, self._sync_exit_stack)

    async def __aenter__(self) -> Self:
        return self  # pragma: no cover

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)

    async def aclose(self) -> None:
        await self.__aexit__(None, None, None)

    def __enter__(self) -> Self:
        return self  # pragma: no cover

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._sync_exit_stack.__exit__(exc_type, exc_val, exc_tb)

    def close(self) -> None:
        self.__exit__(None, None, None)



class SingletonStore(InstanceStore):
    def __init__(
        self,
        exit_stack: contextlib.AsyncExitStack | None = None,
        sync_exit_stack: contextlib.ExitStack | None = None,
    ) -> None:
        super().__init__(exit_stack, sync_exit_stack)
        self._locks: dict[Provider[Any], anyio.Lock] = (
            collections.defaultdict(
                anyio.Lock,
            )
        )
        self._sync_locks: dict[tuple[type[Any], Any], threading.Lock] = (
            collections.defaultdict(
                threading.Lock,
            )
        )

    @contextlib.asynccontextmanager
    async def lock(self, provider: Provider[Any]) -> AsyncIterator[bool]:
        if provider not in self._cache:
            async with self._locks[provider]:
                yield provider not in self._cache
                return
        yield False

    @contextlib.contextmanager
    def sync_lock(
        self,
        provider: Provider[Any],
    ) -> Iterator[bool]:
        if provider not in self._cache:
            with self._sync_locks[provider]:
                yield provider not in self._cache
                return
        yield False
