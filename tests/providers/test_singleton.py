import pytest

from dependency_depression import Singleton


class _Test:
    pass


def test_identity():
    provider = Singleton(_Test)
    instance = provider.provide_sync()
    assert instance is provider.provide_sync()


@pytest.mark.anyio
async def test_identity_async():
    provider = Singleton(_Test)
    instance = provider.provide_sync()
    assert instance is provider.provide_sync() is await provider.provide()
