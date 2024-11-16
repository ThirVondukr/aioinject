from collections.abc import AsyncGenerator, AsyncIterator, Generator, Iterator
from typing import Any
from unittest.mock import patch

import pytest

from aioinject import Provider, providers


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


async def test_provide_async() -> None:
    return_value = 42

    async def factory() -> int:
        return return_value

    provider = providers.Scoped[int](factory)
    assert await provider.provide({}) == return_value


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


def iterable() -> Iterator[int]:
    yield 42


def gen() -> Generator[int, None, None]:
    yield 42


async def async_iterable() -> AsyncIterator[int]:
    yield 42


async def async_gen() -> AsyncGenerator[int, None]:
    yield 42


@pytest.mark.parametrize("factory", [iterable, gen, async_iterable, async_gen])
def test_generator_return_types(factory: Any) -> None:
    provider = providers.Scoped(factory)
    assert provider.type_ is int
