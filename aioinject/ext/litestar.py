import contextlib
from collections.abc import AsyncIterator, Callable
from contextlib import aclosing
from typing import ParamSpec, TypeVar

from litestar import Litestar
from litestar.config.app import AppConfig
from litestar.middleware import MiddlewareProtocol
from litestar.plugins import InitPluginProtocol
from litestar.types import ASGIApp, Receive, Scope, Send

import aioinject
from aioinject import utils
from aioinject.decorators import InjectMethod

_T = TypeVar("_T")
_P = ParamSpec("_P")

_STATE_KEY = "__aioinject_container__"


def inject(function: Callable[_P, _T]) -> Callable[_P, _T]:
    wrapper = aioinject.decorators.inject(
        function,
        inject_method=InjectMethod.context,
    )
    return utils.clear_wrapper(wrapper)


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
        container: aioinject.Container = app.state[_STATE_KEY]
        async with container.context():
            await self.app(scope, receive, send)


class AioInjectPlugin(InitPluginProtocol):
    def __init__(self, container: aioinject.Container) -> None:
        self.container = container

    @contextlib.asynccontextmanager
    async def _lifespan(
        self,
        _: Litestar,
    ) -> AsyncIterator[None]:
        async with aclosing(self.container):
            yield

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        app_config.state[_STATE_KEY] = self.container
        app_config.middleware.append(AioInjectMiddleware)
        app_config.lifespan.append(self._lifespan)
        return app_config
