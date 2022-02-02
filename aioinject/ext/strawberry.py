import contextvars
import functools
from typing import Type

from strawberry.extensions import Extension
from strawberry.utils.await_maybe import AwaitableOrValue

from aioinject import utils
from aioinject.containers import Container
from aioinject.providers import collect_dependencies

container_var: contextvars.ContextVar["Container"] = contextvars.ContextVar(
    "aioinject_container"
)


def _wrap_async(function, inject_annotations):
    @functools.wraps(function)
    async def wrapper(*args, **kwargs):
        container = container_var.get()
        async with container.context() as ctx:
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
    wrapper = utils.clear_wrapper(wrapper, inject_annotations)
    return wrapper


def make_container_ext(container: Container) -> Type[Extension]:
    class ContainerExtension(Extension):
        token: contextvars.Token

        def on_request_start(self) -> AwaitableOrValue[None]:
            self.token = container_var.set(container)

        def on_request_end(self) -> AwaitableOrValue[None]:
            container_var.reset(self.token)

    return ContainerExtension
