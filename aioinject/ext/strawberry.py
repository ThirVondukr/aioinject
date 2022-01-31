import contextvars
import functools
import inspect
import typing
from typing import Any

from aioinject.containers import Container
from aioinject.markers import Inject
from aioinject.providers import collect_dependencies

container_var: contextvars.ContextVar["Container"] = contextvars.ContextVar(
    "aioinject_container"
)


def _clear_wrapper(wrapper: Any, inject_annotations: dict[str, Any]):
    signature = inspect.signature(wrapper)
    new_params = tuple(
        p for p in signature.parameters.values() if p.name not in inject_annotations
    )
    wrapper.__signature__ = signature.replace(parameters=new_params)
    for name in inject_annotations:
        del wrapper.__annotations__[name]


def _wrap_async(function, inject_annotations):
    @functools.wraps(function)
    async def wrapper(*args, **kwargs):
        container = container_var.get()
        with container.context() as ctx:
            dependencies = {}
            for dependency in collect_dependencies(inject_annotations):
                dependencies[dependency.name] = ctx.resolve_sync(
                    interface=dependency.type,
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
    _clear_wrapper(wrapper, inject_annotations)
    return wrapper
