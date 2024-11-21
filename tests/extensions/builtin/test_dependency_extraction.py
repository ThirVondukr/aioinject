from collections.abc import Sequence
from types import NoneType
from typing import Annotated, Generic, TypeVar

import pytest

from aioinject import Container, Inject, Object, Provider, Scoped
from aioinject.extensions.builtin import (
    BuiltinDependencyExtractor,
    ObjectDependencyExtractor,
)
from aioinject.providers import Dependency


class _Test:
    def __init__(self, a: int, b: str) -> None:
        pass


def _factory(a: int, b: str) -> None:
    pass


def _factory_with_annotated(
    a: Annotated[int, Inject()],
) -> None:
    pass


def _no_dependencies() -> None:
    pass


def _factory_mixed(
    a: int,
    service: Annotated[
        dict[str, int],
        Inject(),
    ],
    string: Annotated[str, Inject()],
) -> None:
    pass


T = TypeVar("T")


class GenericService(Generic[T]):
    def __init__(self, dependency: str) -> None:
        self.dependency = dependency


class WithGenericDependency(Generic[T]):
    def __init__(self, dependency: T) -> None:
        self.dependency = dependency


class ConstrainedGenericDependency(WithGenericDependency[int]):
    pass


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


@pytest.mark.parametrize(
    ("provider", "dependencies", "return_type"),
    [
        (
            Scoped(_factory),
            (
                Dependency(name="a", type_=int),
                Dependency(name="b", type_=str),
            ),
            NoneType,
        ),
        (
            Scoped(_Test),
            (
                Dependency(name="a", type_=int),
                Dependency(name="b", type_=str),
            ),
            _Test,
        ),
        (
            Scoped(_factory_with_annotated),
            (Dependency(name="a", type_=int),),
            NoneType,
        ),
        (
            Scoped(_no_dependencies),
            (),
            NoneType,
        ),
        (
            Scoped(_factory_mixed),
            (
                Dependency(
                    name="a",
                    type_=int,
                ),
                Dependency(
                    name="service",
                    type_=dict[str, int],
                ),
                Dependency(
                    name="string",
                    type_=str,
                ),
            ),
            NoneType,
        ),
        (
            Scoped(GenericService[int]),
            (Dependency(name="dependency", type_=str),),
            GenericService[int],
        ),
        (
            Scoped(WithGenericDependency[int]),
            (Dependency(name="dependency", type_=int),),
            WithGenericDependency[int],
        ),
        (
            Scoped(ConstrainedGenericDependency),
            (Dependency(name="dependency", type_=int),),
            ConstrainedGenericDependency,
        ),
    ],
)
def test_builtin_dependency_extractor(
    provider: Provider[object],
    dependencies: Sequence[Dependency[object]],
    return_type: type[object],
) -> None:
    extension = BuiltinDependencyExtractor()
    assert extension.extract_dependencies(provider, {}) == dependencies
    assert extension.extract_type(provider) is return_type


@pytest.mark.parametrize(
    ("provider", "dependencies", "return_type"),
    [
        (
            Object(42),
            (),
            int,
        ),
    ],
)
def test_object_dependency_extractor(
    provider: Provider[object],
    dependencies: Sequence[Dependency[object]],
    return_type: type[object],
) -> None:
    extension = ObjectDependencyExtractor()
    assert extension.extract_dependencies(provider, {}) == dependencies
    assert extension.extract_type(provider) is return_type
