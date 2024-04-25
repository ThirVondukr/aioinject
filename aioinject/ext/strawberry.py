from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, ParamSpec, TypeVar

from strawberry.extensions import SchemaExtension

from aioinject import _utils, decorators
from aioinject.context import container_var


if TYPE_CHECKING:
    from aioinject.containers import Container

__all__ = ["inject", "AioInjectExtension"]

_T = TypeVar("_T")
_P = ParamSpec("_P")


def inject(function: Callable[_P, _T]) -> Callable[_P, _T]:
    wrapper = decorators.inject(
        function,
        inject_method=decorators.InjectMethod.container,
    )
    return _utils.clear_wrapper(wrapper)


class AioInjectExtension(SchemaExtension):
    def __init__(self, container: Container) -> None:
        self.container = container

    def on_operation(
        self,
    ) -> Iterator[None]:
        token = container_var.set(self.container)
        yield
        container_var.reset(token)
