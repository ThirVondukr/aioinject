from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable


if TYPE_CHECKING:
    from aioinject.providers import Dependency

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager

    from aioinject import (
        Container,
        InjectionContext,
        Provider,
        SyncInjectionContext,
    )
    from aioinject._types import T


@runtime_checkable
class LifespanExtension(Protocol):
    def lifespan(
        self,
        container: Container,
    ) -> AbstractAsyncContextManager[None]: ...


@runtime_checkable
class OnInitExtension(Protocol):
    def on_init(
        self,
        container: Container,
    ) -> None: ...


@runtime_checkable
class OnResolveExtension(Protocol):
    async def on_resolve(
        self,
        context: InjectionContext,
        provider: Provider[T],
        instance: T,
    ) -> None: ...


@runtime_checkable
class SyncOnResolveExtension(Protocol):
    def on_resolve_sync(
        self,
        context: SyncInjectionContext,
        provider: Provider[T],
        instance: T,
    ) -> None: ...


@runtime_checkable
class SupportsDependencyExtraction(Protocol):
    def extract_supports(self, provider: Provider[Any]) -> bool: ...

    def extract_dependencies(
        self,
        provider: Provider[Any],
        context: dict[str, Any],
    ) -> tuple[Dependency[object], ...]: ...

    def extract_type(
        self,
        provider: Provider[T],
    ) -> type[T]: ...


Extension = LifespanExtension | OnInitExtension | SupportsDependencyExtraction
ContextExtension = OnResolveExtension
SyncContextExtension = SyncOnResolveExtension
