from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator, Callable
from typing import TYPE_CHECKING, ParamSpec, TypeVar

from litestar import Litestar
from litestar.config.app import AppConfig
from litestar.middleware import MiddlewareProtocol
from litestar.plugins import InitPluginProtocol
from litestar.types import ASGIApp, Receive, Scope, Send

from aioinject import _utils, decorators


if TYPE_CHECKING:
    from aioinject.containers import Container

__all__ = ["inject", "AioInjectMiddleware", "AioInjectPlugin"]

_T = TypeVar("_T")
_P = ParamSpec("_P")

_STATE_KEY = "__aioinject_container__"
_SCOPE_CONTEXT_KEY = "__aioinject_context__"


def inject(function: Callable[_P, _T]) -> Callable[_P, _T]:
    wrapper = decorators.inject(
        function,
        inject_method=decorators.InjectMethod.context,
    )
    return _utils.clear_wrapper(wrapper)


class AioInjectMiddleware(MiddlewareProtocol):
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        app: Litestar = scope["app"]
        container: Container = app.state[_STATE_KEY]

        async with container.context() as ctx:
            scope[_SCOPE_CONTEXT_KEY] = ctx  # type: ignore[literal-required]
            await self.app(scope, receive, send)


async def _after_exception(exception: BaseException, scope: Scope) -> None:
    if _SCOPE_CONTEXT_KEY in scope:
        await scope[_SCOPE_CONTEXT_KEY].__aexit__(  # type: ignore[literal-required]
            type(exception),
            exception,
            exception.__traceback__,
        )


class AioInjectPlugin(InitPluginProtocol):
    def __init__(self, container: Container) -> None:
        self.container = container

    @contextlib.asynccontextmanager
    async def _lifespan(
        self,
        _: Litestar,
    ) -> AsyncIterator[None]:
        async with self.container:
            yield

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        app_config.state[_STATE_KEY] = self.container
        app_config.middleware.append(AioInjectMiddleware)
        app_config.lifespan.append(self._lifespan)
        app_config.after_exception.append(_after_exception)
        return app_config
