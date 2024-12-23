import sys
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


# TODO: I'm pretty sure this redundant.
class NestedGenericService(Generic[T]):
    def __init__(self, service: T) -> None:
        self.service = service

MEANING_OF_LIFE = 42
class Something:
    def __init__(self) -> None:
        self.a = MEANING_OF_LIFE

async def test_nested_generics() -> None:
    container = Container()
    container.register(
        Scoped(NestedGenericService[WithGenericDependency[Something]]),
    Scoped(WithGenericDependency[Something]),
    Scoped(Something),
    Object(MEANING_OF_LIFE),
    Object("42"))

    async with container.context() as ctx:
        instance = await ctx.resolve(NestedGenericService[WithGenericDependency[Something]])
        assert isinstance(instance, NestedGenericService)
        assert isinstance(instance.service, WithGenericDependency)
        assert isinstance(instance.service.dependency, Something)
        assert instance.service.dependency.a == MEANING_OF_LIFE

IS_PY_312 = sys.version_info >= (3, 12)
skip_ifnot_312 = pytest.mark.skipif(not IS_PY_312, reason="Python 3.12+ required")

class TestNestedUnresolvedGeneric(Generic[T]):
    def __init__(self, service:  WithGenericDependency[T]) -> None:
        self.service = service


async def test_nested_unresolved_generic() -> None:
    container = Container()
    container.register(Scoped(TestNestedUnresolvedGeneric[int]),
    Scoped(WithGenericDependency[int]),
    Object(42),
    Object("42"))

    async with container.context() as ctx:
        instance = await ctx.resolve(TestNestedUnresolvedGeneric[int])
        assert isinstance(instance, TestNestedUnresolvedGeneric)
        assert isinstance(instance.service, WithGenericDependency)
        assert instance.service.dependency == 42





async def test_nested_unresolved_concrete_generic() -> None:
    class GenericImpl(TestNestedUnresolvedGeneric[str]):
        pass
    

    container = Container()
    container.register(Scoped(GenericImpl),
    Scoped(WithGenericDependency[str]),
    Object(42),
    Object("42"))

    async with container.context() as ctx:
        instance = await ctx.resolve(GenericImpl)
        assert isinstance(instance, GenericImpl)
        assert isinstance(instance.service, WithGenericDependency)
        assert instance.service.dependency == "42"