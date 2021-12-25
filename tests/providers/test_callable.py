from unittest.mock import patch

import pytest

from dependency_depression import providers


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


def test_would_pass_kwargs_into_factory(provider):
    with patch.object(provider, "factory") as factory_mock:
        provider.provide_sync()
        factory_mock.assert_called_once_with()

    kwargs = {"a": 1, "b": 2}
    with patch.object(provider, "factory") as factory_mock:
        provider.provide_sync(**kwargs)
        factory_mock.assert_called_once_with(**kwargs)


def test_would_return_factory_result(provider):
    instance = object()
    with patch.object(provider, "factory") as factory_mock:
        factory_mock.return_value = instance
        assert provider.provide_sync() is instance


@pytest.mark.anyio
async def test_provide_async():
    async def factory() -> int:
        return 42

    provider = providers.Callable(int, factory)
    assert await provider.provide() == 42
