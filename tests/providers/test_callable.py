from collections import defaultdict
from typing import Annotated, AsyncGenerator, AsyncIterable, Generator, Iterable
from unittest.mock import patch

import pytest

from dependency_depression import Impl, Inject, NoCache, providers
from dependency_depression.providers import _Dependency


class _Test:
    pass


@pytest.fixture
def provider():
    return providers.Callable(_Test)


def test_can_provide(provider):
    instance = provider.provide_sync()
    assert isinstance(instance, _Test)


def test_provided_instances_are_unique(provider):
    first = (provider.provide_sync(),)
    second = provider.provide_sync()
    assert first is not second


def test_would_pass_kwargs_into_impl(provider):
    with patch.object(provider, "impl") as factory_mock:
        provider.provide_sync()
        factory_mock.assert_called_once_with()

    kwargs = {"a": 1, "b": 2}
    with patch.object(provider, "impl") as factory_mock:
        provider.provide_sync(**kwargs)
        factory_mock.assert_called_once_with(**kwargs)


def test_would_return_factory_result(provider):
    instance = object()
    with patch.object(provider, "impl") as factory_mock:
        factory_mock.return_value = instance
        assert provider.provide_sync() is instance


@pytest.mark.anyio
async def test_provide_async():
    async def factory() -> int:
        return 42

    provider = providers.Callable(factory)
    assert await provider.provide() == 42


def test_type_hints():
    def factory(a: int, b: str) -> None:
        pass

    provider = providers.Callable(factory)
    expected = {
        "a": int,
        "b": str,
    }
    assert provider.type_hints == expected


def test_type_hints_on_class():
    class Test:
        def __init__(self, a: int, b: str):
            pass

    provider = providers.Callable(Test)
    expected = {
        "a": int,
        "b": str,
    }
    assert provider.type_hints == expected


def test_annotated_type_hint():
    def factory(
        a: Annotated[int, Inject, NoCache],
    ) -> None:
        pass

    provider = providers.Callable(factory)
    assert provider.type_hints == {"a": Annotated[int, Inject, NoCache]}


def test_should_specify_return_type():
    def factory():
        pass

    with pytest.raises(ValueError):
        providers.Callable(factory)

    def factory_with_return() -> None:
        pass

    providers.Callable(factory_with_return)


def test_is_async_on_sync():
    def factory() -> None:
        pass

    provider = providers.Callable(factory)
    assert not provider.is_async


def test_is_async_on_async():
    async def factory() -> None:
        pass

    provider = providers.Callable(factory)
    assert provider.is_async


def test_empty_dependencies():
    def factory() -> None:
        pass

    provider = providers.Callable(factory)
    assert provider.dependencies == tuple()


def test_does_not_collect_dependencies_not_annotated_with_inject():
    def factory(
        a: int,
        b: Annotated[int, Impl[bool]],
        c: Annotated[int, NoCache],
    ) -> None:
        pass

    provider = providers.Callable(factory)
    assert provider.dependencies == tuple()


def test_dependencies():
    def factory(
        a: int,
        service: Annotated[dict[str, int], Inject[defaultdict]],
        string: Annotated[str, Inject, NoCache],
    ) -> None:
        pass

    provider = providers.Callable(factory)
    expected = (
        _Dependency(
            name="service", interface=dict[str, int], impl=defaultdict, use_cache=True
        ),
        _Dependency(name="string", interface=str, impl=None, use_cache=False),
    )
    assert provider.dependencies == expected


def test_generator_return_types():
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
