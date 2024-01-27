import contextlib
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

import pytest

from aioinject import Scoped, Singleton, providers
from aioinject.containers import Container
from aioinject.context import InjectionContext


class _AbstractService:
    pass


class _ServiceA(_AbstractService):
    pass


class _ServiceB(_AbstractService):
    pass


@pytest.fixture
def container() -> Container:
    return Container()


def test_can_init(container: Container) -> None:
    assert container


def test_can_retrieve_context(container: Container) -> None:
    ctx = container.context()
    assert isinstance(ctx, InjectionContext)


def test_can_register_single(container: Container) -> None:
    provider = providers.Scoped(_ServiceA)
    container.register(provider)

    expected = {_ServiceA: provider}
    assert container.providers == expected


def test_cant_register_multiple_providers_for_same_type(
    container: Container,
) -> None:
    container.register(Scoped(int))

    with pytest.raises(
        ValueError,
        match="^Provider for type <class 'int'> is already registered$",
    ):
        container.register(Scoped(int))


def test_can_retrieve_single_provider(container: Container) -> None:
    int_provider = providers.Scoped(int)
    container.register(int_provider)
    assert container.get_provider(int)


def test_missing_provider() -> None:
    container = Container()
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011
        assert container.get_provider(_ServiceA)

    msg = f"Provider for type {_ServiceA.__qualname__} not found"
    assert str(exc_info.value) == msg


@pytest.mark.anyio
async def test_should_close_singletons() -> None:
    shutdown = False

    @contextlib.asynccontextmanager
    async def dependency() -> AsyncIterator[int]:
        nonlocal shutdown

        yield 42
        shutdown = True

    provider = Singleton(dependency)

    container = Container()
    container.register(provider)
    for _ in range(2):
        async with container.context() as ctx:
            assert await ctx.resolve(int) == 42  # noqa: PLR2004
    assert shutdown is False

    await container.aclose()
    assert shutdown is True


@pytest.mark.anyio
async def test_deffered_dependecies() -> None:
    if TYPE_CHECKING:
        from decimal import Decimal

    def some_deffered_type() -> "Decimal":
        from decimal import Decimal

        return Decimal("1.0")

    class DoubledDecimal:
        def __init__(self, decimal: "Decimal") -> None:
            self.decimal = decimal * 2

    container = Container()

    def register_decimal_scoped() -> None:
        from decimal import Decimal

        container.register(Scoped(some_deffered_type, Decimal))

    register_decimal_scoped()
    container.register(Scoped(DoubledDecimal))
    async with container.context() as ctx:
        assert (await ctx.resolve(DoubledDecimal)).decimal == DoubledDecimal(
            some_deffered_type(),
        ).decimal
