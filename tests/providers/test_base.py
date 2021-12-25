from collections import defaultdict
from typing import Annotated, AsyncGenerator, AsyncIterable, Generator, Iterable

import pytest

from dependency_depression import providers
from dependency_depression.markers import Impl, Inject, NoCache
from dependency_depression.providers import _Dependency


def test_type_hints():
    def factory(a: int, b: str) -> None:
        pass

    provider = providers.Provider(None, factory)
    expected = {
        "a": int,
        "b": str,
    }
    assert provider.type_hints == expected


def test_type_hints_on_class():
    class Test:
        def __init__(self, a: int, b: str):
            pass

    provider = providers.Provider(Test)
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

    provider = providers.Provider(None, factory)
    assert provider.type_hints == {"a": Annotated[int, Inject, NoCache]}


def test_should_specify_return_type():
    def factory():
        pass

    with pytest.raises(ValueError):
        providers.Provider(None, factory)

    def factory_with_return() -> None:
        pass

    providers.Provider(None, factory_with_return)


def test_is_async_on_sync():
    def factory() -> None:
        pass

    provider = providers.Provider(None, factory)
    assert not provider.is_async


def test_is_async_on_async():
    async def factory() -> None:
        pass

    provider = providers.Provider(None, factory)
    assert provider.is_async


def test_empty_dependencies():
    def factory() -> None:
        pass

    provider = providers.Provider(None, factory)
    assert provider.dependencies == tuple()


def test_does_not_collect_dependencies_not_annotated_with_inject():
    def factory(
        a: int,
        b: Annotated[int, Impl[bool]],
        c: Annotated[int, NoCache],
    ) -> None:
        pass

    provider = providers.Provider(None, factory)
    assert provider.dependencies == tuple()


def test_dependencies():
    def factory(
        a: int,
        service: Annotated[dict[str, int], Inject, Impl[defaultdict]],
        string: Annotated[str, Inject, NoCache],
    ) -> None:
        pass

    provider = providers.Provider(None, factory)
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
        provider = providers.Callable(None, factory)
        assert provider.impl is int
