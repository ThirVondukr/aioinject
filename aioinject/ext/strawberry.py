import contextvars
from typing import TypeVar

from strawberry.extensions import Extension
from strawberry.utils.await_maybe import AwaitableOrValue

import aioinject
from aioinject import utils
from aioinject.containers import Container
from aioinject.context import container_var
from aioinject.decorators import InjectMethod

_T = TypeVar("_T")


def inject(function: _T) -> _T:
    wrapper = aioinject.decorators.inject(
        function,
        inject_method=InjectMethod.container,
    )
    return utils.clear_wrapper(wrapper)


def make_container_ext(container: Container) -> type[Extension]:
    class ContainerExtension(Extension):
        token: contextvars.Token

        def on_request_start(self) -> AwaitableOrValue[None]:
            self.token = container_var.set(container)
            return None  # noqa: RET501

        def on_request_end(self) -> AwaitableOrValue[None]:
            container_var.reset(self.token)
            return None  # noqa: RET501

    return ContainerExtension
