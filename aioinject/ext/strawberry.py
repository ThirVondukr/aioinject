from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, ParamSpec, TypeVar

from strawberry.extensions import SchemaExtension

from aioinject import decorators, utils
from aioinject.context import container_var


if TYPE_CHECKING:
    from aioinject.containers import Container

_T = TypeVar("_T")
_P = ParamSpec("_P")


def inject(function: Callable[_P, _T]) -> Callable[_P, _T]:
    wrapper = decorators.inject(
        function,
        inject_method=decorators.InjectMethod.container,
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
