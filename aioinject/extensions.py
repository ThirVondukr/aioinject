from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable


if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager

    from aioinject import Container, Provider
    from aioinject import InjectionContext, SyncInjectionContext
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
    def on_resolve(
        self,
        context: SyncInjectionContext,
        provider: Provider[T],
        instance: T,
    ) -> None: ...


Extension = LifespanExtension | OnInitExtension
ContextExtension = OnResolveExtension | SyncOnResolveExtension
