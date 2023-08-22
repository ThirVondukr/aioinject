import pytest

from aioinject import Provider, Singleton


class _Test:
    pass


def test_identity() -> None:
    provider = Singleton(_Test)
    instance = provider.provide_sync()
    assert instance is provider.provide_sync()


@pytest.mark.anyio
async def test_identity_async() -> None:
    provider = Singleton(_Test)
    instance = provider.provide_sync()
    assert instance is provider.provide_sync() is await provider.provide()


@pytest.mark.anyio
async def test_async_function() -> None:
    async def create_test() -> _Test:
        return _Test()

    provider = Singleton[_Test](factory=create_test)
    instance = await provider.provide()
    assert instance is await provider.provide()


@pytest.mark.anyio
async def test_should_not_provide_none_twice() -> None:
    count = 0

    async def func() -> None:
        nonlocal count
        count += 1

    provider: Provider[None] = Singleton(func)
    for _ in range(5):
        assert await provider.provide() is None  # type: ignore[func-returns-value]
        assert count == 1
