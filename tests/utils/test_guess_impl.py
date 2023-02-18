from collections.abc import AsyncGenerator, AsyncIterable, Generator, Iterable

import pytest

from aioinject.providers import _guess_impl


def test_class():
    class A:
        pass

    assert _guess_impl(A) is A


def test_function():
    def factory() -> int:
        return 42

    async def async_factory() -> int:
        return 42

    assert _guess_impl(factory) is int
    assert _guess_impl(async_factory) is int


def test_function_with_no_return_annotation():
    def factory():
        pass

    with pytest.raises(ValueError):
        _guess_impl(factory)


def test_iterables():
    def iterable() -> Iterable[int]:
        yield 42

    async def async_iterable() -> AsyncIterable[int]:
        yield 42

    def generator() -> Generator[int, None, None]:
        yield 42

    async def async_generator() -> AsyncGenerator[int, None]:
        yield 42

    factories = [iterable, async_iterable, generator, async_generator]

    for factory in factories:
        assert _guess_impl(factory) is int
