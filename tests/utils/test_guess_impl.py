from collections.abc import (
    AsyncGenerator,
    AsyncIterable,
    AsyncIterator,
    Generator,
    Iterable,
    Iterator,
)
from typing import TypeAlias

import pytest

from aioinject.providers import _guess_impl


def test_class() -> None:
    class A:
        pass

    assert _guess_impl(A) is A


def test_function() -> None:
    def factory() -> int:
        return 42

    async def async_factory() -> int:
        return 42

    assert _guess_impl(factory) is int
    assert _guess_impl(async_factory) is int


def test_function_with_no_return_annotation() -> None:
    def factory():  # noqa: ANN202
        pass

    with pytest.raises(ValueError) as exc_info:  # noqa: PT011
        _guess_impl(factory)

    msg = f"factory {factory.__qualname__} does not specify return type."
    assert str(exc_info.value) == msg


@pytest.mark.parametrize(
    "return_type",
    [
        Iterable[int],
        Iterator[int],
        Generator[int, None, None],
    ],
)
def test_sync_iterables(return_type: TypeAlias) -> None:
    def iterable() -> return_type:
        ...

    assert _guess_impl(iterable) is int


@pytest.mark.parametrize(
    "return_type",
    [
        AsyncIterable[int],
        AsyncIterator[int],
        AsyncGenerator[int, None],
    ],
)
def test_async_iterables(return_type: TypeAlias) -> None:
    async def iterable() -> return_type:
        ...

    assert _guess_impl(iterable) is int
