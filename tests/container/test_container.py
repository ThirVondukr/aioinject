import contextlib
from collections.abc import AsyncIterator, Iterator

import pytest

from aioinject import Scoped, Singleton, providers
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
    assert container


def test_can_retrieve_context(container: Container) -> None:
    ctx = container.context()
    assert isinstance(ctx, InjectionContext)


def test_can_register_single(container: Container) -> None:
    provider = providers.Scoped(_ServiceA)
    container.register(provider)

    expected = {_ServiceA: provider}
    assert {
        key: provider.provider for key, provider in container.providers.items()
    } == expected


def test_can_register_batch(container: Container) -> None:
    provider1 = providers.Scoped(_ServiceA)
    provider2 = providers.Scoped(_ServiceB)
    container.register(provider1, provider2)
    excepted = {_ServiceA: provider1, _ServiceB: provider2}
    assert {
        key: provider.provider for key, provider in container.providers.items()
    } == excepted


def test_cant_register_multiple_providers_for_same_type(
    container: Container,
) -> None:
    container.register(Scoped(int))

    with pytest.raises(
        ValueError,
        match="^Provider for type <class 'int'> is already registered$",
    ):
        container.register(Scoped(int))


def test_can_retrieve_single_provider(container: Container) -> None:
    int_provider = providers.Scoped(int)
    container.register(int_provider)
    assert container.get_provider(int)


def test_missing_provider() -> None:
    container = Container()
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011
        assert container.get_provider(_ServiceA)

    msg = f"Provider for type {_ServiceA.__qualname__} not found"
    assert str(exc_info.value) == msg


async def test_should_close_singletons() -> None:
    shutdown = False

    @contextlib.asynccontextmanager
    async def dependency() -> AsyncIterator[int]:
        nonlocal shutdown

        yield 42
        shutdown = True

    container = Container()
    container.register(Singleton(dependency))
    async with container:
        for _ in range(2):
            async with container.context() as ctx:
                assert await ctx.resolve(int) == 42  # noqa: PLR2004

        assert shutdown is False
    assert shutdown is True


def test_should_close_singletons_sync() -> None:
    shutdown = False

    @contextlib.contextmanager
    def dependency() -> Iterator[int]:
        nonlocal shutdown
        yield 42
        shutdown = True

    container = Container()
    container.register(Singleton(dependency))
    with container:
        for _ in range(2):
            with container.sync_context() as ctx:
                assert ctx.resolve(int) == 42  # noqa: PLR2004

        assert shutdown is False
    assert shutdown is True


def test_dependency_extractor_not_found() -> None:
    provider = Singleton(_ServiceA)
    container = Container(default_extensions=[])
    with pytest.raises(ValueError) as err_info:  # noqa: PT011
        container.register(provider)
    assert (
        str(err_info.value)
        == f"Couldn't find appropriate SupportsDependencyExtraction extension for provider {provider!r}"
    )
