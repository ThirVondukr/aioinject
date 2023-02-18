import pytest

from aioinject import providers
from aioinject.containers import Container
from aioinject.context import InjectionContext


class _AbstractService:
    pass


class _ServiceA(_AbstractService):
    pass


class _ServiceB(_AbstractService):
    pass


@pytest.fixture
def container() -> Container:
    return Container()


def test_can_init(container: Container) -> None:
    Container()


def test_can_retrieve_context(container: Container) -> None:
    ctx = container.context()
    assert isinstance(ctx, InjectionContext)


def test_can_register_single(container: Container) -> None:
    provider = providers.Callable(_ServiceA)
    container.register(provider)

    expected = {_ServiceA: [provider]}
    assert container.providers == expected


def test_can_register_multi(container: Container) -> None:
    provider_a = providers.Callable(_ServiceA)
    provider_b = providers.Callable(_ServiceB)
    container.register(provider_a)
    container.register(provider_b)

    expected = {_ServiceA: [provider_a], _ServiceB: [provider_b]}
    assert container.providers == expected


def test_can_retrieve_single_provider(container: Container) -> None:
    int_provider = providers.Callable(int)
    container.register(int_provider)
    assert container.get_provider(int)


@pytest.fixture
def multi_provider_container(container: Container) -> Container:
    a_provider = providers.Callable(_ServiceA, type_=_AbstractService)
    b_provider = providers.Callable(_ServiceB, type_=_AbstractService)
    container.register(a_provider)
    container.register(b_provider)
    return container


def test_get_provider_raises_error_if_multiple_providers(
    multi_provider_container: Container,
) -> None:
    with pytest.raises(ValueError):
        assert multi_provider_container.get_provider(_AbstractService)


def test_can_get_multi_provider_if__specified(multi_provider_container: Container) -> None:
    assert multi_provider_container.get_provider(_AbstractService, _ServiceA)
    assert multi_provider_container.get_provider(_AbstractService, _ServiceB)


def test_missing_provider() -> None:
    container = Container()
    with pytest.raises(ValueError):
        assert container.get_provider(_ServiceA)
