from typing import Generic, TypeVar

import pytest

from aioinject import Container, Object, Scoped
from aioinject.providers import Dependency


T = TypeVar("T")


class GenericService(Generic[T]):
    def __init__(self, dependency: str) -> None:
        self.dependency = dependency


class WithGenericDependency(Generic[T]):
    def __init__(self, dependency: T) -> None:
        self.dependency = dependency


class ConstrainedGenericDependency(WithGenericDependency[int]):
    pass


async def test_generic_dependency() -> None:
    assert Scoped(GenericService[int]).resolve_dependencies() == (
        Dependency(
            name="dependency",
            type_=str,
        ),
    )

    assert Scoped(WithGenericDependency[int]).resolve_dependencies() == (
        Dependency(
            name="dependency",
            type_=int,
        ),
    )
    assert Scoped(ConstrainedGenericDependency).resolve_dependencies() == (
        Dependency(
            name="dependency",
            type_=int,
        ),
    )


@pytest.mark.parametrize(
    ("type_", "instanceof"),
    [
        (GenericService, GenericService),
        (WithGenericDependency[int], WithGenericDependency),
        (ConstrainedGenericDependency, ConstrainedGenericDependency),
    ],
)
async def test_resolve_generics(
    type_: type[object],
    instanceof: type[object],
) -> None:
    container = Container()
    container.register(Scoped(type_))
    container.register(Object(42))
    container.register(Object("42"))

    async with container.context() as ctx:
        instance = await ctx.resolve(type_)
        assert isinstance(instance, instanceof)



class NestedGenericService(Generic[T]):
    def __init__(self, service: GenericService[T]) -> None:
        self.service = service


async def test_nested_generics() -> None:
    container = Container()
    container.register(Scoped(NestedGenericService[int]),
    Scoped(GenericService[int]),
    Object(42),
    Object("42"))

    async with container.context() as ctx:
        instance = await ctx.resolve(NestedGenericService[int])
        assert isinstance(instance, NestedGenericService)
        assert isinstance(instance.service, GenericService)
        assert instance.service.dependency == "42"