from __future__ import annotations

import contextvars
import inspect
from collections.abc import Callable, Coroutine, Iterable, Mapping, Sequence
from contextvars import ContextVar
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
    overload,
)

from typing_extensions import Self

from aioinject._store import InstanceStore, NotInCache
from aioinject._types import AnyCtx, T
from aioinject.extensions import (
    ContextExtension, OnResolveExtension, SyncOnResolveExtension
)
from aioinject.providers import Dependency, DependencyLifetime


if TYPE_CHECKING:
    from aioinject import Provider, _types
    from aioinject.containers import Container

_T = TypeVar("_T")

context_var: ContextVar[AnyCtx] = ContextVar("aioinject_context")
container_var: ContextVar[Container] = ContextVar("aioinject_container")


class _BaseInjectionContext:
    def __init__(
        self,
        container: Container,
        singletons: InstanceStore,
        extensions: Sequence[ContextExtension],
    ) -> None:
        self._container = container
        self._extensions = extensions

        self._singletons = singletons
        self._store = InstanceStore()

        self._token: contextvars.Token[AnyCtx] | None = None
        self._providers: _types.Providers[Any] = {}

    def _get_store(self, lifetime: DependencyLifetime) -> InstanceStore:
        if lifetime is DependencyLifetime.singleton:
            return self._singletons
        return self._store

    def _get_provider(self, type_: type[_T]) -> Provider[_T]:
        return self._providers.get(type_) or self._container.get_provider(
            type_,
        )

    def register(self, provider: Provider[Any]) -> None:
        self._providers[provider.type_] = provider


class InjectionContext(_BaseInjectionContext):
    async def resolve(
        self,
        type_: type[_T],
    ) -> _T:
        provider = self._get_provider(type_)
        store = self._get_store(provider.lifetime)
        if (cached := store.get(provider)) is not NotInCache.sentinel:
            return cached

        dependencies = {}
        for dependency in provider.resolve_dependencies(
            self._container.type_context,
        ):
            dependencies[dependency.name] = await self.resolve(
                type_=dependency.type_,
            )

        if provider.lifetime is DependencyLifetime.singleton:
            async with store.lock(provider) as should_provide:
                if should_provide:
                    return await self._resolve(provider, store, dependencies)
                return store.get(  # type: ignore[return-value] # pragma: no cover
                    provider,
                )

        return await self._resolve(provider, store, dependencies)

    async def _resolve(
        self,
        provider: Provider[_T],
        store: InstanceStore,
        dependencies: Mapping[str, Any],
    ) -> _T:
        resolved = await provider.provide(dependencies)
        if provider.is_generator:
            resolved = await store.enter_context(resolved)
        store.add(provider, resolved)
        await self._on_resolve(provider=provider, instance=resolved)
        return resolved

    @overload
    async def execute(
        self,
        function: Callable[..., Coroutine[Any, Any, _T]],
        dependencies: Iterable[Dependency[object]],
        *args: Any,
        **kwargs: Any,
    ) -> _T: ...

    @overload
    async def execute(
        self,
        function: Callable[..., _T],
        dependencies: Iterable[Dependency[object]],
        *args: Any,
        **kwargs: Any,
    ) -> _T: ...

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

    async def _on_resolve(self, provider: Provider[T], instance: T) -> None:
        for extension in self._extensions:
            if isinstance(extension, OnResolveExtension):
                await extension.on_resolve(self, provider, instance)

    async def __aenter__(self) -> Self:
        self._token = context_var.set(self)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        context_var.reset(self._token)  # type: ignore[arg-type]
        await self._store.__aexit__(exc_type, exc_val, exc_tb)


class SyncInjectionContext(_BaseInjectionContext):
    def resolve(
        self,
        type_: type[_T],
    ) -> _T:
        provider = self._get_provider(type_)
        store = self._get_store(provider.lifetime)
        if (cached := store.get(provider)) is not NotInCache.sentinel:
            return cached

        dependencies = {}
        for dependency in provider.resolve_dependencies(
            self._container.type_context,
        ):
            dependencies[dependency.name] = self.resolve(
                type_=dependency.type_,
            )

        if provider.lifetime is DependencyLifetime.singleton:
            with store.sync_lock(provider) as should_provide:
                if should_provide:
                    return self._resolve(provider, store, dependencies)
                return store.get(provider)  # type: ignore[return-value] # pragma: no cover

        return self._resolve(provider, store, dependencies)

    def _resolve(
        self,
        provider: Provider[_T],
        store: InstanceStore,
        dependencies: Mapping[str, Any],
    ) -> _T:
        resolved = provider.provide_sync(dependencies)
        if provider.is_generator:
            resolved = store.enter_sync_context(resolved)
        store.add(provider, resolved)
        self._on_resolve(provider=provider, instance=resolved)
        return resolved

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

    def _on_resolve(self, provider: Provider[T], instance: T) -> None:
        for extension in self._extensions:
            if isinstance(extension, SyncOnResolveExtension):
                extension.on_resolve(self, provider, instance)

    def __enter__(self) -> Self:
        self._token = context_var.set(self)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        context_var.reset(self._token)  # type: ignore[arg-type]
        self._store.__exit__(exc_type, exc_val, exc_tb)
