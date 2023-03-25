from collections.abc import Callable, Iterator
from typing import ParamSpec, TypeVar

from strawberry.extensions import SchemaExtension

import aioinject
from aioinject import utils
from aioinject.containers import Container
from aioinject.context import container_var
from aioinject.decorators import InjectMethod

_T = TypeVar("_T")
_P = ParamSpec("_P")


def inject(function: Callable[_P, _T]) -> Callable[_P, _T]:
    wrapper = aioinject.decorators.inject(
        function,
        inject_method=InjectMethod.container,
    )
    return utils.clear_wrapper(wrapper)


class ContainerExtension(SchemaExtension):
    def __init__(self, container: Container) -> None:
        self.container = container

    def on_operation(
        self,
    ) -> Iterator[None]:
        token = container_var.set(self.container)
        yield
        container_var.reset(token)
