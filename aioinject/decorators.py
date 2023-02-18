import enum
import functools
import inspect
from collections.abc import Callable, Coroutine
from typing import Any, ParamSpec, TypeVar

from aioinject import InjectionContext, SyncInjectionContext
from aioinject.context import container_var, context_var
from aioinject.providers import collect_dependencies

_T = TypeVar("_T")
_P = ParamSpec("_P")


class InjectMethod(enum.Enum):
    container = enum.auto()
    context = enum.auto()


def _get_context(
    inject_method: InjectMethod,
    *,
    is_async: bool,
) -> InjectionContext | SyncInjectionContext:
    if inject_method is InjectMethod.container:
        container = container_var.get()
        return container.context() if is_async else container.sync_context()
    return context_var.get()


def _wrap_async(
    function: Callable[_P, Coroutine[Any, Any, _T]],
    inject_method: InjectMethod,
) -> Callable[_P, Coroutine[Any, Any, _T]]:
    dependencies = list(collect_dependencies(function))

    @functools.wraps(function)
    async def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _T:
        context = _get_context(inject_method, is_async=True)
        execute = context.execute(
            function,
            dependencies,
            *args,
            **kwargs,
        )

        if inject_method is InjectMethod.container:
            async with context:
                return await execute

        return await execute

    return wrapper


def _wrap_sync(
    function: Callable[_P, _T],
    inject_method: InjectMethod,
) -> Callable[_P, _T]:
    dependencies = list(collect_dependencies(function))

    @functools.wraps(function)
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _T:
        context = _get_context(inject_method, is_async=False)
        execute = functools.partial(
            context.execute,
            function,
            dependencies,
            *args,
            **kwargs,
        )

        if inject_method is InjectMethod.container:
            with context:
                return execute()  # type: ignore[return-value]

        return execute()  # type: ignore[return-value]

    return wrapper


def inject(func=None, inject_method=InjectMethod.context):
    def wrap(function):
        if inspect.iscoroutinefunction(function):
            return _wrap_async(function, inject_method=inject_method)
        return _wrap_sync(function, inject_method=inject_method)

    if func is None:
        return wrap

    return wrap(func)
