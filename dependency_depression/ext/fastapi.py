import functools
import typing
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint, DispatchFunction
from starlette.responses import Response
from starlette.types import ASGIApp

from dependency_depression import Depression, Inject
from dependency_depression.context import context_var
from dependency_depression.providers import collect_dependencies
from dependency_depression.utils import clear_wrapper


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
    inject_annotations = {
        name: annotation
        for name, annotation in typing.get_type_hints(
            function, include_extras=True
        ).items()
        if Inject in typing.get_args(annotation)
    }
    wrapper = _wrap_async(function, inject_annotations)
    clear_wrapper(wrapper, inject_annotations)
    return wrapper


class InjectMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        container: Depression,
        dispatch: Optional[DispatchFunction] = None,
    ) -> None:
        super().__init__(app, dispatch)
        self.container = container

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        async with self.container.context():
            return await call_next(request)
