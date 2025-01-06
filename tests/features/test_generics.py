import abc
from collections.abc import Awaitable, Callable
from typing import Generic, TypeVar

import pytest

from aioinject import Container, Object, Scoped
from aioinject.providers import Dependency, Transient


T = TypeVar("T")
ReqT = TypeVar("ReqT")
ResT = TypeVar("ResT")


class GenericService(Generic[T]):
    def __init__(self, dependency: str) -> None:
        self.dependency = dependency


class WithGenericDependency(Generic[T]):
    def __init__(self, dependency: T) -> None:
        self.dependency = dependency


class ConstrainedGenericDependency(WithGenericDependency[int]):
    pass


async def test_generic_dependency() -> None:
    assert Scoped(GenericService[int]).collect_dependencies() == (
        Dependency(
            name="dependency",
            type_=str,
        ),
    )

    assert Scoped(WithGenericDependency[int]).collect_dependencies() == (
        Dependency(
            name="dependency",
            type_=int,
        ),
    )
    assert Scoped(ConstrainedGenericDependency).collect_dependencies() == (
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
    def __init__(self, service: T) -> None:
        self.service = service


MEANING_OF_LIFE_INT = 42
MEANING_OF_LIFE_STR = "42"


class Something:
    def __init__(self) -> None:
        self.a = MEANING_OF_LIFE_INT


async def test_nested_generics() -> None:
    container = Container()
    container.register(
        Scoped(NestedGenericService[WithGenericDependency[Something]]),
        Scoped(WithGenericDependency[Something]),
        Scoped(Something),
        Object(MEANING_OF_LIFE_INT),
        Object("42"),
    )

    async with container.context() as ctx:
        instance = await ctx.resolve(
            NestedGenericService[WithGenericDependency[Something]]
        )
        assert isinstance(instance, NestedGenericService)
        assert isinstance(instance.service, WithGenericDependency)
        assert isinstance(instance.service.dependency, Something)
        assert instance.service.dependency.a == MEANING_OF_LIFE_INT


class NestedUnresolvedGeneric(Generic[T]):
    def __init__(self, service: WithGenericDependency[T]) -> None:
        self.service = service


async def test_nested_unresolved_generic() -> None:
    container = Container()
    container.register(
        Scoped(NestedUnresolvedGeneric[int]),
        Scoped(WithGenericDependency[int]),
        Object(42),
        Object("42"),
    )

    async with container.context() as ctx:
        instance = await ctx.resolve(NestedUnresolvedGeneric[int])
        assert isinstance(instance, NestedUnresolvedGeneric)
        assert isinstance(instance.service, WithGenericDependency)
        assert instance.service.dependency == MEANING_OF_LIFE_INT


async def test_nested_unresolved_concrete_generic() -> None:
    class GenericImpl(NestedUnresolvedGeneric[str]):
        pass

    container = Container()
    container.register(
        Scoped(GenericImpl),
        Scoped(WithGenericDependency[str]),
        Object(42),
        Object("42"),
    )

    async with container.context() as ctx:
        instance = await ctx.resolve(GenericImpl)
        assert isinstance(instance, GenericImpl)
        assert isinstance(instance.service, WithGenericDependency)
        assert instance.service.dependency == "42"


async def test_partially_resolved_generic() -> None:
    K = TypeVar("K")

    class TwoGeneric(Generic[T, K]):
        def __init__(
            self, a: WithGenericDependency[T], b: WithGenericDependency[K]
        ) -> None:
            self.a = a
            self.b = b

    class UsesTwoGeneric(Generic[T]):
        def __init__(self, service: TwoGeneric[T, str]) -> None:
            self.service = service

    container = Container()
    container.register(
        Scoped(UsesTwoGeneric[int]),
        Scoped(TwoGeneric[int, str]),
        Scoped(WithGenericDependency[int]),
        Scoped(WithGenericDependency[str]),
        Object(MEANING_OF_LIFE_INT),
        Object("42"),
    )

    async with container.context() as ctx:
        instance = await ctx.resolve(UsesTwoGeneric[int])
        assert isinstance(instance, UsesTwoGeneric)
        assert isinstance(instance.service, TwoGeneric)
        assert isinstance(instance.service.a, WithGenericDependency)
        assert isinstance(instance.service.b, WithGenericDependency)
        assert instance.service.a.dependency == MEANING_OF_LIFE_INT
        assert instance.service.b.dependency == MEANING_OF_LIFE_STR


async def test_can_resolve_generic_class_without_parameters() -> None:
    class GenericClass(Generic[T]):
        def __init__(self, a: int) -> None:
            self.a = a

        def so_generic(self) -> T:  # pragma: no cover
            raise NotImplementedError

    container = Container()
    container.register(Scoped(GenericClass), Object(MEANING_OF_LIFE_INT))

    async with container.context() as ctx:
        instance = await ctx.resolve(GenericClass)
        assert isinstance(instance, GenericClass)
        assert instance.a == MEANING_OF_LIFE_INT


async def test_can_resolve_generic_iterable() -> None:
    class MiddlewareBase(abc.ABC, Generic[ReqT, ResT]):
        @abc.abstractmethod
        async def __call__(
            self,
            request: ReqT,
            handle: Callable[[ReqT], Awaitable[ResT]],
        ) -> ResT:
            pass

    class FirstMiddleware(MiddlewareBase[ReqT, ResT]):
        async def __call__(
            self,
            request: ReqT,
            handle: Callable[[ReqT], Awaitable[ResT]],
        ) -> ResT:
            return await handle(request)

    class SecondMiddleware(MiddlewareBase[ReqT, ResT]):
        async def __call__(
            self,
            request: ReqT,
            handle: Callable[[ReqT], Awaitable[ResT]],
        ) -> ResT:
            return await handle(request)

    class ThirdMiddleware(MiddlewareBase[ReqT, ResT]):
        async def __call__(
            self,
            request: ReqT,
            handle: Callable[[ReqT], Awaitable[ResT]],
        ) -> ResT:
            return await handle(request)

    container = Container()
    container.register(
        Transient(FirstMiddleware, MiddlewareBase[str, str]),
        Transient(SecondMiddleware, MiddlewareBase[int, int]),
        Transient(ThirdMiddleware, MiddlewareBase[int, int]),
    )

    async with container.context() as ctx:
        instances = await ctx.resolve_iterable(MiddlewareBase[int, int])  # type: ignore[type-abstract]
        assert len(instances) == 2  # noqa: PLR2004
        assert isinstance(instances[0], SecondMiddleware)
        assert isinstance(instances[1], ThirdMiddleware)
