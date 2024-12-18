from __future__ import annotations
import types
from typing_extensions import Annotated, TypeGuard
import typing as t
import sys

import contextvars
import inspect
from collections.abc import Callable, Coroutine, Iterable, Mapping, Sequence
from contextvars import ContextVar
from types import GenericAlias, TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    TypeVar,
    overload,
)

from litestar.utils import is_generic
from typing_extensions import Self

from aioinject._store import InstanceStore, NotInCache
from aioinject._types import AnyCtx, T
from aioinject.extensions import (
    ContextExtension,
    OnResolveExtension,
    SyncContextExtension,
    SyncOnResolveExtension,
)
from aioinject.providers import Dependency, DependencyLifetime


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
    ) -> None:
        self._container = container
        self._extensions = extensions

        self._singletons = singletons
        self._store = InstanceStore()

        self._token: contextvars.Token[AnyCtx] | None = None
        self._providers: _types.Providers[Any] = {}

        self._closed = False

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


def is_generic_alias(type_: Any) -> TypeGuard[GenericAlias]:
    return isinstance(type_, types.GenericAlias | t._GenericAlias) and type_ not in (int, tuple, list, dict, set)


class InjectionContext(_BaseInjectionContext[ContextExtension]):
    async def resolve(
        self,
        type_: type[_T],
    ) -> _T:
        provider = self._get_provider(type_)
        store = self._get_store(provider.lifetime)
        if (cached := store.get(provider)) is not NotInCache.sentinel:
            return cached

        dependencies = {}
        args_map: dict[str, Any] = {}
        if type_is_generic := is_generic_alias(type_):
            args = type_.__args__
            params = type_.__origin__.__parameters__
            for param, arg in zip(params, args, strict=False):
                args_map[param.__name__] = arg



        for dependency in provider.resolve_dependencies(
            self._container.type_context,
        ):
            if type_is_generic and is_generic_alias(dependency.type_):
                # This is a generic type, we need to resolve the type arguments
                # and pass them to the provider.
                resolved_args = [
                    args_map[arg.__name__]
                    for arg in
                    t.get_args(dependency.type_)

                ]
                resolved_type = dependency.type_[*resolved_args]
                dependencies[dependency.name] = await self.resolve(
                    type_=resolved_type,
                )
            else:
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
        if self._closed:
            return

        await self._store.__aexit__(exc_type, exc_val, exc_tb)
        context_var.reset(self._token)  # type: ignore[arg-type]
        self._closed = True


class SyncInjectionContext(_BaseInjectionContext[SyncContextExtension]):
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
