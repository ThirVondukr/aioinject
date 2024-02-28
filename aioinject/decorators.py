import enum
import functools
import inspect
from collections.abc import AsyncIterable, AsyncIterator, Callable, Coroutine
from typing import Any, ParamSpec, TypeVar, overload

from aioinject import InjectionContext, SyncInjectionContext
from aioinject.context import container_var, context_var
from aioinject.providers import collect_dependencies


_T = TypeVar("_T")
_P = ParamSpec("_P")
_ContextT = TypeVar("_ContextT", InjectionContext, SyncInjectionContext)


class InjectMethod(enum.Enum):
    container = enum.auto()
    context = enum.auto()


def _get_context(
    inject_method: InjectMethod,
    *,
    context_type: type[_ContextT],
) -> _ContextT:
    if inject_method is InjectMethod.container:
        container = container_var.get()
        if issubclass(context_type, InjectionContext):
            return container.context()
        return container.sync_context()
    return context_var.get()  # type: ignore[return-value]


def _wrap_async(
    function: Callable[_P, Coroutine[Any, Any, _T]],
    inject_method: InjectMethod,
) -> Callable[_P, Coroutine[Any, Any, _T]]:
    dependencies = list(collect_dependencies(function))

    @functools.wraps(function)
    async def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _T:
        context = _get_context(inject_method, context_type=InjectionContext)
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


def _wrap_async_gen(
    function: Callable[_P, Coroutine[Any, Any, AsyncIterable[_T]]],
    inject_method: InjectMethod,
) -> Callable[_P, AsyncIterable[_T]]:
    wrapped = _wrap_async(function, inject_method)

    @functools.wraps(function)
    async def wrapper(
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> AsyncIterator[_T]:
        async for element in await wrapped(*args, **kwargs):
            yield element

    return wrapper


def _wrap_sync(
    function: Callable[_P, _T],
    inject_method: InjectMethod,
) -> Callable[_P, _T]:
    dependencies = list(collect_dependencies(function))

    @functools.wraps(function)
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _T:
        context = _get_context(
            inject_method,
            context_type=SyncInjectionContext,
        )
        execute = functools.partial(
            context.execute,
            function,
            dependencies,
            *args,
            **kwargs,
        )

        if inject_method is InjectMethod.container:
            with context:
                return execute()

        return execute()

    return wrapper


@overload
def inject(
    func: Callable[_P, _T],
    *,
    inject_method: InjectMethod = InjectMethod.context,
) -> Callable[_P, _T]: ...


@overload
def inject(
    *,
    inject_method: InjectMethod = InjectMethod.context,
) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]: ...


def inject(
    func: Callable[_P, _T] | None = None,
    *,
    inject_method: InjectMethod = InjectMethod.context,
) -> Callable[_P, _T] | Callable[[Callable[_P, _T]], Callable[_P, _T]]:
    def wrap(function: Callable[_P, _T]) -> Callable[_P, _T]:
        if inspect.iscoroutinefunction(function):
            return _wrap_async(
                function,
                inject_method=inject_method,
            )  # type: ignore[return-value]

        if inspect.isasyncgenfunction(function):
            return _wrap_async_gen(  # type: ignore[return-value]
                function,  # type: ignore[arg-type]
                inject_method=inject_method,
            )
        return _wrap_sync(function, inject_method=inject_method)

    if func is None:
        return wrap

    return wrap(func)
