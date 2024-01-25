from collections.abc import AsyncGenerator, AsyncIterator, Generator, Iterator
from typing import Annotated
from unittest.mock import patch

import pytest

from aioinject import Inject, Provider, providers
from aioinject.providers import Dependency


class _Test:
    pass


@pytest.fixture
def provider() -> Provider[_Test]:
    return providers.Scoped(_Test)


def test_can_provide(provider: Provider[_Test]) -> None:
    instance = provider.provide_sync({})
    assert isinstance(instance, _Test)


def test_would_pass_kwargs_into_impl(provider: Provider[_Test]) -> None:
    with patch.object(provider, "impl") as factory_mock:
        provider.provide_sync({})
        factory_mock.assert_called_once_with()

    kwargs = {"a": 1, "b": 2}
    with patch.object(provider, "impl") as factory_mock:
        provider.provide_sync(kwargs)
        factory_mock.assert_called_once_with(**kwargs)


def test_would_return_factory_result(provider: Provider[_Test]) -> None:
    instance = object()
    with patch.object(provider, "impl") as factory_mock:
        factory_mock.return_value = instance
        assert provider.provide_sync({}) is instance


@pytest.mark.anyio
async def test_provide_async() -> None:
    return_value = 42

    async def factory() -> int:
        return return_value

    provider = providers.Scoped[int](factory)
    assert await provider.provide({}) == return_value


def test_type_hints_on_function() -> None:
    def factory(a: int, b: str) -> None:  # noqa: ARG001
        pass

    provider = providers.Scoped(factory)
    expected = {
        "a": Annotated[int, Inject],
        "b": Annotated[str, Inject],
    }
    assert provider.type_hints == expected


def test_type_hints_on_class() -> None:
    class Test:
        def __init__(self, a: int, b: str) -> None:
            pass

    provider = providers.Scoped(Test)
    expected = {
        "a": Annotated[int, Inject],
        "b": Annotated[str, Inject],
    }
    assert provider.type_hints == expected


def test_annotated_type_hint() -> None:
    def factory(
        a: Annotated[int, Inject()],  # noqa: ARG001
    ) -> None:
        pass

    provider = providers.Scoped(factory)
    assert provider.type_hints == {
        "a": Annotated[int, Inject()],
    }


def test_is_async_on_sync() -> None:
    def factory() -> None:
        pass

    provider = providers.Scoped[None](factory)
    assert not provider.is_async


def test_is_async_on_async() -> None:
    async def factory() -> None:
        pass

    provider = providers.Scoped[None](factory)
    assert provider.is_async


def test_empty_dependencies() -> None:
    def factory() -> None:
        pass

    provider = providers.Scoped(factory)
    assert provider.dependencies == ()


def test_dependencies() -> None:
    def factory(
        a: int,  # noqa: ARG001
        service: Annotated[  # noqa: ARG001
            dict[str, int],
            Inject(),
        ],
        string: Annotated[str, Inject()],  # noqa: ARG001
    ) -> None:
        pass

    provider = providers.Scoped(factory)
    expected = (
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
    )
    assert provider.resolve_dependencies() == expected


def iterable() -> Iterator[int]:
    yield 42


def gen() -> Generator[int, None, None]:
    yield 42


async def async_iterable() -> AsyncIterator[int]:
    yield 42


async def async_gen() -> AsyncGenerator[int, None]:
    yield 42


@pytest.mark.parametrize("factory", [iterable, gen, async_iterable, async_gen])
def test_generator_return_types(factory) -> None:
    provider = providers.Scoped(factory)
    assert provider.resolve_type() is int
