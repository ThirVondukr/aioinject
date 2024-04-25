from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, ParamSpec, TypeVar

from aioinject import _utils, decorators


if TYPE_CHECKING:
    from starlette.types import ASGIApp, Receive, Scope, Send

    from aioinject.containers import Container

__all__ = ["inject", "AioInjectMiddleware"]

_T = TypeVar("_T")
_P = ParamSpec("_P")


def inject(function: Callable[_P, _T]) -> Callable[_P, _T]:
    wrapper = decorators.inject(
        function,
        inject_method=decorators.InjectMethod.context,
    )
    return _utils.clear_wrapper(wrapper)


class AioInjectMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        container: Container,
    ) -> None:
        self.app = app
        self.container = container

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        async with self.container.context():
            await self.app(scope, receive, send)
