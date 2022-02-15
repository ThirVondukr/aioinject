import enum
import functools
import inspect

from aioinject.context import container_var, context_var
from aioinject.providers import collect_dependencies


class InjectMethod(enum.Enum):
    container = enum.auto()
    context = enum.auto()


def _get_context(inject_method: InjectMethod):
    if inject_method is InjectMethod.container:
        return container_var.get().context()
    return context_var.get()


def _wrap_async(
    function,
    inject_method: InjectMethod,
):
    dependencies = list(collect_dependencies(function))

    @functools.wraps(function)
    async def wrapper(*args, **kwargs):
        context = _get_context(inject_method)
        execute = functools.partial(
            context.execute, function, dependencies, *args, **kwargs
        )

        if inject_method is InjectMethod.container:
            async with context:
                return await execute()

        return await execute()

    return wrapper


def _wrap_sync(function, inject_method: InjectMethod):
    dependencies = list(collect_dependencies(function))

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        context = _get_context(inject_method)
        execute = functools.partial(
            context.execute, function, dependencies, *args, **kwargs
        )

        if inject_method is InjectMethod.container:
            with context:
                return execute()

        return execute()

    return wrapper


def inject(func=None, inject_method=InjectMethod.context):
    def wrap(function):
        if inspect.iscoroutinefunction(function):
            return _wrap_async(function, inject_method=inject_method)
        return _wrap_sync(function, inject_method=inject_method)

    if func is None:
        return wrap

    return wrap(func)
