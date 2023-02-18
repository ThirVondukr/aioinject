from collections import defaultdict
from collections.abc import AsyncGenerator, AsyncIterable, Generator, Iterable
from typing import Annotated
from unittest.mock import patch

import pytest

from aioinject import Inject, Provider, providers
from aioinject.providers import Dependency


class _Test:
    pass


@pytest.fixture
def provider() -> Provider:
    return providers.Callable(_Test)


def test_can_provide(provider: Provider) -> None:
    instance = provider.provide_sync()
    assert isinstance(instance, _Test)


def test_provided_instances_are_unique(provider: Provider) -> None:
    first = provider.provide_sync()
    second = provider.provide_sync()
    assert first is not second


def test_would_pass_kwargs_into_impl(provider: Provider) -> None:
    with patch.object(provider, "impl") as factory_mock:
        provider.provide_sync()
        factory_mock.assert_called_once_with()

    kwargs = {"a": 1, "b": 2}
    with patch.object(provider, "impl") as factory_mock:
        provider.provide_sync(**kwargs)
        factory_mock.assert_called_once_with(**kwargs)


def test_would_return_factory_result(provider: Provider) -> None:
    instance = object()
    with patch.object(provider, "impl") as factory_mock:
        factory_mock.return_value = instance
        assert provider.provide_sync() is instance


@pytest.mark.anyio
async def test_provide_async() -> None:
    return_value = 42

    async def factory() -> int:
        return return_value

    provider = providers.Callable(factory)
    assert await provider.provide() == return_value


def test_type_hints_on_function() -> None:
    def factory(a: int, b: str) -> None:  # noqa: ARG001
        pass

    provider = providers.Callable(factory)
    expected = {
        "a": Annotated[int, Inject],
        "b": Annotated[str, Inject],
    }
    assert provider.type_hints == expected


def test_type_hints_on_class() -> None:
    class Test:
        def __init__(self, a: int, b: str) -> None:
            pass

    provider = providers.Callable(Test)
    expected = {
        "a": Annotated[int, Inject],
        "b": Annotated[str, Inject],
    }
    assert provider.type_hints == expected


def test_annotated_type_hint() -> None:
    def factory(
        a: Annotated[int, Inject(cache=False)],  # noqa: ARG001
    ) -> None:
        pass

    provider = providers.Callable(factory)
    assert provider.type_hints == {"a": Annotated[int, Inject(cache=False)]}


def test_should_specify_return_type() -> None:
    def factory():  # noqa: ANN202
        pass

    with pytest.raises(ValueError):
        providers.Callable(factory)

    def factory_with_return() -> None:
        pass

    providers.Callable(factory_with_return)


def test_is_async_on_sync() -> None:
    def factory() -> None:
        pass

    provider = providers.Callable(factory)
    assert not provider.is_async


def test_is_async_on_async() -> None:
    async def factory() -> None:
        pass

    provider = providers.Callable(factory)
    assert provider.is_async


def test_empty_dependencies() -> None:
    def factory() -> None:
        pass

    provider = providers.Callable(factory)
    assert provider.dependencies == ()


def test_dependencies() -> None:
    def factory(
        a: int,  # noqa: ARG001
        service: Annotated[  # noqa: ARG001
            dict[str, int],
            Inject(defaultdict),
        ],
        string: Annotated[str, Inject(cache=False)],  # noqa: ARG001
    ) -> None:
        pass

    provider = providers.Callable(factory)
    expected = (
        Dependency(
            name="a",
            type=int,
            implementation=None,
            use_cache=True,
        ),
        Dependency(
            name="service",
            type=dict[str, int],
            implementation=defaultdict,
            use_cache=True,
        ),
        Dependency(
            name="string",
            type=str,
            implementation=None,
            use_cache=False,
        ),
    )
    assert provider.dependencies == expected


def test_generator_return_types() -> None:
    def iterable() -> Iterable[int]:
        yield 42

    def gen() -> Generator[int, None, None]:
        yield 42

    async def async_iterable() -> AsyncIterable[int]:
        yield 42

    async def async_gen() -> AsyncGenerator[int, None]:
        yield 42

    factories = [iterable, gen, async_iterable, async_gen]
    for factory in factories:
        provider = providers.Callable(factory)
        assert provider.type is int
