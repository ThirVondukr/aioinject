import functools
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint, DispatchFunction
from starlette.responses import Response
from starlette.types import ASGIApp

from aioinject import Container, utils
from aioinject.context import context_var
from aioinject.providers import collect_dependencies
from aioinject.utils import clear_wrapper


def _wrap_async(function, inject_annotations):
    @functools.wraps(function)
    async def wrapper(*args, **kwargs):
        ctx = context_var.get()
        dependencies = {}
        for dependency in collect_dependencies(inject_annotations):
            dependencies[dependency.name] = await ctx.resolve(
                type_=dependency.type,
                impl=dependency.implementation,
                use_cache=dependency.use_cache,
            )
        return await function(*args, **kwargs, **dependencies)

    return wrapper


def inject(function):
    inject_annotations = utils.get_inject_annotations(function)
    wrapper = _wrap_async(function, inject_annotations)
    clear_wrapper(wrapper, inject_annotations)
    return wrapper


class InjectMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        container: Container,
        dispatch: Optional[DispatchFunction] = None,
    ) -> None:
        super().__init__(app, dispatch)
        self.container = container

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        async with self.container.context():
            return await call_next(request)
