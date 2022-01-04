import pytest

from dependency_depression import providers
from dependency_depression.containers import Depression
from dependency_depression.context import DepressionContext


class _AbstractService:
    pass


class _ServiceA(_AbstractService):
    pass


class _ServiceB(_AbstractService):
    pass


@pytest.fixture
def container() -> Depression:
    return Depression()


def test_can_init(container):
    Depression()


def test_can_retrieve_context(container):
    ctx = container.context()
    assert isinstance(ctx, DepressionContext)


def test_can_register_single(container):
    provider = providers.Callable(_ServiceA)
    container.register(provider)

    expected = {_ServiceA: [provider]}
    assert container.providers == expected


def test_can_register_multi(container):
    provider_a = providers.Callable(_ServiceA)
    provider_b = providers.Callable(_ServiceB)
    container.register(provider_a)
    container.register(provider_b)

    expected = {
        _ServiceA: [provider_a],
        _ServiceB: [provider_b]
    }
    assert container.providers == expected


def test_can_retrieve_single_provider(container):
    int_provider = providers.Callable(int)
    container.register(int_provider)
    assert container.get_provider(int)


@pytest.fixture
def multi_provider_container(container):
    a_provider = providers.Callable(_ServiceA, type_=_AbstractService)
    b_provider = providers.Callable(_ServiceB, type_=_AbstractService)
    container.register(a_provider)
    container.register(b_provider)
    return container


def test_get_provider_raises_error_if_multiple_providers(multi_provider_container):
    with pytest.raises(ValueError):
        assert multi_provider_container.get_provider(_AbstractService)


def test_can_get_multi_provider_if__specified(multi_provider_container):
    assert multi_provider_container.get_provider(_AbstractService, _ServiceA)
    assert multi_provider_container.get_provider(_AbstractService, _ServiceB)
