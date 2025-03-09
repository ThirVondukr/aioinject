from __future__ import annotations

import contextvars
import inspect
from collections import defaultdict
from collections.abc import Callable, Coroutine, Iterable, Mapping, Sequence
from contextvars import ContextVar
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Literal,
    TypeVar,
    overload,
)

from typing_extensions import Self

from aioinject._features.generics import get_generic_parameter_map
from aioinject._store import InstanceStore, NotInCache
from aioinject._types import AnyCtx, T
from aioinject.extensions import (
    ContextExtension,
    OnResolveExtension,
    SyncContextExtension,
    SyncOnResolveExtension,
)
from aioinject.providers import Dependency, DependencyLifetime, Object


if TYPE_CHECKING:
    from aioinject import Provider, _types
    from aioinject.containers import Container

_T = TypeVar("_T")
_TExtension = TypeVar("_TExtension")

context_var: ContextVar[AnyCtx] = ContextVar("aioinject_context")
container_var: ContextVar[Container] = ContextVar("aioinject_container")


class _BaseInjectionContext(Generic[_TExtension]):
    def __init__(
        self,
        container: Container,
        singletons: InstanceStore,
        extensions: Sequence[_TExtension],
        context: Mapping[Any, Any] | None = None,
    ) -> None:
        self._container = container
        self._extensions = extensions

        self._singletons = singletons
        self._store = InstanceStore()

        self._token: contextvars.Token[AnyCtx] | None = None
        self._providers: _types.Providers[Any] = defaultdict(list)

        if context:
            for key, value in context.items():
                self.register(Object(value, type_=key))

        self._closed = False

    def _get_store(self, lifetime: DependencyLifetime) -> InstanceStore:
        if lifetime is DependencyLifetime.singleton:
            return self._singletons
        return self._store

    def _get_providers(self, type_: type[_T]) -> list[Provider[_T]]:
        return self._providers.get(type_) or self._container.get_providers(
            type_,
        )

    def register(self, provider: Provider[Any]) -> None:
        self._providers[provider.type_].append(provider)


class InjectionContext(_BaseInjectionContext[ContextExtension]):
    async def resolve(self, type_: type[_T]) -> _T:
        return await self._resolve(type_, is_iterable=False)

    async def resolve_iterable(self, type_: type[_T]) -> list[_T]:
        return await self._resolve(type_, is_iterable=True)

    @overload
    async def _resolve(
        self,
        type_: type[_T],
        *,
        is_iterable: Literal[False],
    ) -> _T: ...

    @overload
    async def _resolve(
        self,
        type_: type[_T],
        *,
        is_iterable: Literal[True],
    ) -> list[_T]: ...

    async def _resolve(
        self,
        type_: type[_T],
        *,
        is_iterable: bool,
    ) -> _T | list[_T]:
        providers = self._get_providers(type_)
        if not is_iterable:
            return await self._resolve_provider(providers[-1])  # type: ignore[arg-type]
        return [
            await self._resolve_provider(provider) for provider in providers
        ]

    async def _resolve_provider(
        self,
        provider: Provider[_T],
    ) -> _T:
        store = self._get_store(provider.lifetime)
        if (cached := store.get(provider)) is not NotInCache.sentinel:
            return cached

        provider_dependencies = provider.collect_dependencies(
            context=self._container.type_context
        )
        dependencies_map = get_generic_parameter_map(
            provider.type_,  # type: ignore[arg-type]
            provider_dependencies,
        )
        dependencies = {
            dependency.name: await self._resolve(  # type: ignore[call-overload]
                type_=dependencies_map.get(
                    dependency.name,
                    dependency.inner_type,
                ),
                is_iterable=dependency.is_iterable,
            )
            for dependency in provider_dependencies
        }

        if provider.lifetime is DependencyLifetime.singleton:
            async with store.lock(provider) as should_provide:
                if should_provide:
                    return await self._provide_and_store(
                        provider, store, dependencies
                    )
                return store.get(provider)  # type: ignore[return-value] # pragma: no cover

        return await self._provide_and_store(provider, store, dependencies)

    async def _provide_and_store(
        self,
        provider: Provider[_T],
        store: InstanceStore,
        dependencies: Mapping[str, object],
    ) -> _T:
        provided = await provider.provide(dependencies)
        if provider.is_generator:
            provided = await store.enter_context(provided)
        store.add(provider, provided)
        await self._on_resolve(provider=provider, instance=provided)
        return provided

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
        resolved = {
            dependency.name: await self._resolve(  # type: ignore[call-overload]
                type_=dependency.inner_type,
                is_iterable=dependency.is_iterable,
            )
            for dependency in dependencies
            if dependency.name not in kwargs
        }

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
        if self._closed:
            return

        await self._store.__aexit__(exc_type, exc_val, exc_tb)
        context_var.reset(self._token)  # type: ignore[arg-type]
        self._closed = True


class SyncInjectionContext(_BaseInjectionContext[SyncContextExtension]):
    def resolve(self, type_: type[_T]) -> _T:
        return self._resolve(type_, is_iterable=False)

    def resolve_iterable(self, type_: type[_T]) -> list[_T]:
        return self._resolve(type_, is_iterable=True)

    @overload
    def _resolve(
        self,
        type_: type[_T],
        *,
        is_iterable: Literal[False],
    ) -> _T: ...

    @overload
    def _resolve(
        self,
        type_: type[_T],
        *,
        is_iterable: Literal[True],
    ) -> list[_T]: ...

    def _resolve(
        self,
        type_: type[_T],
        *,
        is_iterable: bool,
    ) -> _T | list[_T]:
        providers = self._get_providers(type_)
        if not is_iterable:
            return self._resolve_provider(providers[-1])
        return [self._resolve_provider(provider) for provider in providers]

    def _resolve_provider(
        self,
        provider: Provider[_T],
    ) -> _T:
        store = self._get_store(provider.lifetime)
        if (cached := store.get(provider)) is not NotInCache.sentinel:
            return cached

        provider_dependencies = provider.collect_dependencies(
            context=self._container.type_context
        )
        dependencies_map = get_generic_parameter_map(
            provider.type_,  # type: ignore[arg-type]
            provider_dependencies,
        )
        dependencies = {
            dependency.name: self._resolve(  # type: ignore[call-overload]
                type_=dependencies_map.get(
                    dependency.name,
                    dependency.inner_type,
                ),
                is_iterable=dependency.is_iterable,
            )
            for dependency in provider_dependencies
        }

        if provider.lifetime is DependencyLifetime.singleton:
            with store.sync_lock(provider) as should_provide:
                if should_provide:
                    return self._provide_and_store(
                        provider, store, dependencies
                    )
                return store.get(provider)  # type: ignore[return-value] # pragma: no cover

        return self._provide_and_store(provider, store, dependencies)

    def _provide_and_store(
        self,
        provider: Provider[_T],
        store: InstanceStore,
        dependencies: Mapping[str, object],
    ) -> _T:
        provided = provider.provide_sync(dependencies)
        if provider.is_generator:
            provided = store.enter_sync_context(provided)
        store.add(provider, provided)
        self._on_resolve(provider=provider, instance=provided)
        return provided

    def execute(
        self,
        function: Callable[..., _T],
        dependencies: Iterable[Dependency[object]],
        *args: Any,
        **kwargs: Any,
    ) -> _T:
        resolved = {
            dependency.name: self._resolve(  # type: ignore[call-overload]
                type_=dependency.inner_type,
                is_iterable=dependency.is_iterable,
            )
            for dependency in dependencies
            if dependency.name not in kwargs
        }
        return function(*args, **kwargs, **resolved)

    def _on_resolve(self, provider: Provider[T], instance: T) -> None:
        for extension in self._extensions:
            if isinstance(extension, SyncOnResolveExtension):
                extension.on_resolve_sync(self, provider, instance)

    def __enter__(self) -> Self:
        self._token = context_var.set(self)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._closed:  # pragma: no cover
            return

        self._store.__exit__(exc_type, exc_val, exc_tb)
        context_var.reset(self._token)  # type: ignore[arg-type]
        self._closed = True
