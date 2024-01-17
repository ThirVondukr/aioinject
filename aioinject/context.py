from __future__ import annotations

import contextvars
import inspect
from collections.abc import Callable, Coroutine, Iterable, Iterator
from contextvars import ContextVar
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    TypeAlias,
    TypeVar,
    Union,
    overload,
)

from typing_extensions import Self

from aioinject._store import InstanceStore, NotInCache
from aioinject.providers import Dependency, DependencyLifetime


if TYPE_CHECKING:
    from aioinject.containers import Container

_T = TypeVar("_T")

_AnyCtx: TypeAlias = Union["InjectionContext", "SyncInjectionContext"]

context_var: ContextVar[_AnyCtx] = ContextVar("aioinject_context")
container_var: ContextVar[Container] = ContextVar("aioinject_container")


class _BaseInjectionContext:
    def __init__(
        self,
        container: Container,
        singletons: InstanceStore,
    ) -> None:
        self._container = container
        store = InstanceStore()
        self._stores = {
            DependencyLifetime.singleton: singletons,
            DependencyLifetime.scoped: store,
            DependencyLifetime.transient: store,
        }
        self._token: contextvars.Token[_AnyCtx] | None = None

    @property
    def _stores_to_finalize(self) -> Iterator[InstanceStore]:
        for lifetime, store in self._stores.items():
            if lifetime is DependencyLifetime.singleton:
                continue
            yield store


class InjectionContext(_BaseInjectionContext):
    # @profile
    async def resolve(
        self,
        type_: type[_T],
    ) -> _T:
        provider = self._container.get_provider(type_)
        store = self._stores[provider.lifetime]
        if (cached := store.get(provider)) is not NotInCache.sentinel:
            return cached

        dependencies = {
            dep.name: await self.resolve(type_=dep.type_)
            for dep in provider.dependencies
        }
        async with store.lock(provider) as should_provide:
            if should_provide:
                resolved = await store.enter_context(
                    await provider.provide(**dependencies),
                )
                store.add(provider, resolved)
                return resolved
        # It's safe to just call store.get here
        return store.get(provider)  # type: ignore[return-value]

    @overload
    async def execute(
        self,
        function: Callable[..., Coroutine[Any, Any, _T]],
        dependencies: Iterable[Dependency[object]],
        *args: Any,
        **kwargs: Any,
    ) -> _T:
        ...

    @overload
    async def execute(
        self,
        function: Callable[..., _T],
        dependencies: Iterable[Dependency[object]],
        *args: Any,
        **kwargs: Any,
    ) -> _T:
        ...

    async def execute(
        self,
        function: Callable[..., Coroutine[Any, Any, _T] | _T],
        dependencies: Iterable[Dependency[object]],
        *args: Any,
        **kwargs: Any,
    ) -> _T:
        resolved = {}
        for dependency in dependencies:
            if dependency.name in kwargs:
                continue

            resolved[dependency.name] = await self.resolve(
                type_=dependency.type_,
            )
        if inspect.iscoroutinefunction(function):
            return await function(*args, **kwargs, **resolved)
        return function(*args, **kwargs, **resolved)  # type: ignore[return-value]

    async def __aenter__(self) -> Self:
        self._token = context_var.set(self)
        for store in self._stores.values():
            await store.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        context_var.reset(self._token)  # type: ignore[arg-type]
        for store in self._stores_to_finalize:
            await store.__aexit__(exc_type, exc_val, exc_tb)


class SyncInjectionContext(_BaseInjectionContext):
    def resolve(
        self,
        type_: type[_T],
    ) -> _T:
        provider = self._container.get_provider(type_)
        store = self._stores[provider.lifetime]
        if (cached := store.get(provider)) is not NotInCache.sentinel:
            return cached

        dependencies = {
            dep.name: self.resolve(type_=dep.type_)
            for dep in provider.dependencies
        }
        with store.sync_lock(provider) as should_provide:
            if should_provide:
                resolved = store.enter_sync_context(
                    provider.provide_sync(**dependencies),
                )
                store.add(provider, resolved)
                return resolved

        return store.get(provider)  # type: ignore[return-value]

    def execute(
        self,
        function: Callable[..., _T],
        dependencies: Iterable[Dependency[object]],
        *args: Any,
        **kwargs: Any,
    ) -> _T:
        resolved = {}
        for dependency in dependencies:
            if dependency.name in kwargs:
                continue
            resolved[dependency.name] = self.resolve(type_=dependency.type_)
        return function(*args, **kwargs, **resolved)

    def __enter__(self) -> Self:
        self._token = context_var.set(self)
        for store in self._stores.values():
            store.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        context_var.reset(self._token)  # type: ignore[arg-type]
        for store in self._stores_to_finalize:
            store.__exit__(exc_type, exc_val, exc_tb)
