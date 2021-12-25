import pytest

from dependency_depression import providers
from dependency_depression.containers import Depression
from dependency_depression.context import DepressionContext


@pytest.fixture
def container() -> Depression:
    return Depression()


def test_can_init(container):
    Depression()


def test_can_retrieve_context(container):
    ctx = container.context()
    assert isinstance(ctx, DepressionContext)


def test_can_register_single(container):
    provider = providers.Callable(int)
    container.register(int, provider)

    expected = {int: [provider]}
    assert container.providers == expected


def test_can_register_multi(container):
    int_provider = providers.Callable(int)
    bool_provider = providers.Callable(bool)
    container.register(int, int_provider)
    container.register(int, bool_provider)

    expected = {int: [int_provider, bool_provider]}
    assert container.providers == expected


def test_can_retrieve_single_provider(container):
    int_provider = providers.Callable(int)
    container.register(int, int_provider)
    assert container.get_provider(int)


@pytest.fixture
def multi_provider_container(container):
    int_provider = providers.Callable(int)
    bool_provider = providers.Callable(bool)
    container.register(int, int_provider)
    container.register(int, bool_provider)
    return container


def test_get_provider_raises_error_if_multiple_providers(multi_provider_container):
    with pytest.raises(ValueError):
        assert multi_provider_container.get_provider(int)


def test_can_get_multi_provider_if_impl_specified(multi_provider_container):
    assert multi_provider_container.get_provider(int, int)
    assert multi_provider_container.get_provider(int, bool)
