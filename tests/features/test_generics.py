from typing import Generic, TypeVar

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


async def test_resolve_generics() -> None:
    container = Container()
    container.register(Scoped(WithGenericDependency[int]))
    container.register(Object(42))

    async with container.context() as ctx:
        instance = await ctx.resolve(WithGenericDependency[int])
        assert isinstance(instance, WithGenericDependency)
