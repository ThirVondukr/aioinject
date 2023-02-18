import pytest

from aioinject import Singleton


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

    provider = Singleton(factory=create_test)
    instance = await provider.provide()
    assert instance is await provider.provide()
