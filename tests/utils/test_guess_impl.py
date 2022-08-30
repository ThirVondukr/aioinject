from typing import AsyncGenerator, AsyncIterable, Generator, Iterable

import pytest

from aioinject.providers import _guess_impl


def test_class():
    class A:
        pass

    assert _guess_impl(A) is A


def test_function():
    def factory() -> int:
        pass

    async def async_factory() -> int:
        pass

    assert _guess_impl(factory) is int
    assert _guess_impl(async_factory) is int


def test_function_with_no_return_annotation():
    def factory():
        pass

    with pytest.raises(ValueError):
        _guess_impl(factory)


def test_iterables():
    def iterable() -> Iterable[int]:
        pass

    def async_iterable() -> AsyncIterable[int]:
        pass

    def generator() -> Generator[int, None, None]:
        pass

    def async_generator() -> AsyncGenerator[int, None]:
        pass

    factories = [iterable, async_iterable, generator, async_generator]

    for factory in factories:
        assert _guess_impl(factory) is int
