import contextvars
from typing import Type

from strawberry.extensions import Extension
from strawberry.utils.await_maybe import AwaitableOrValue

import aioinject
from aioinject import utils
from aioinject.containers import Container
from aioinject.context import container_var
from aioinject.decorators import InjectMethod


def inject(function):
    wrapper = aioinject.decorators.inject(
        function,
        inject_method=InjectMethod.container,
    )
    wrapper = utils.clear_wrapper(wrapper)
    return wrapper


def make_container_ext(container: Container) -> Type[Extension]:
    class ContainerExtension(Extension):
        token: contextvars.Token

        def on_request_start(self) -> AwaitableOrValue[None]:
            self.token = container_var.set(container)

        def on_request_end(self) -> AwaitableOrValue[None]:
            container_var.reset(self.token)

    return ContainerExtension
