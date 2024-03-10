from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import TYPE_CHECKING, Protocol, runtime_checkable


if TYPE_CHECKING:
    from aioinject import Container


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


Extension = LifespanExtension | OnInitExtension
