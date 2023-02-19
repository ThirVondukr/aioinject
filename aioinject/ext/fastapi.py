from collections.abc import Callable
from typing import ParamSpec, TypeVar

from fastapi import Request
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    DispatchFunction,
    RequestResponseEndpoint,
)
from starlette.responses import Response
from starlette.types import ASGIApp

import aioinject
from aioinject import Container, utils
from aioinject.decorators import InjectMethod

_T = TypeVar("_T")
_P = ParamSpec("_P")


def inject(function: Callable[_P, _T]) -> Callable[_P, _T]:
    wrapper = aioinject.decorators.inject(
        function,
        inject_method=InjectMethod.context,
    )
    return utils.clear_wrapper(wrapper)


class InjectMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        container: Container,
        dispatch: DispatchFunction | None = None,
    ) -> None:
        super().__init__(app, dispatch)
        self.container = container

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        async with self.container.context():
            return await call_next(request)
