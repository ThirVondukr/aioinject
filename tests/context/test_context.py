from typing import Annotated

import pytest
from aioinject import Callable, providers
from aioinject.containers import Container
from aioinject.markers import Inject


class _Session:
    pass


class _Repository:
    def __init__(self, session: Annotated[_Session, Inject]) -> None:
        self.session = session


class _Service:
    def __init__(self, repository: Annotated[_Repository, Inject]) -> None:
        self.repository = repository


@pytest.fixture()
def container() -> Container:
    container = Container()
    container.register(providers.Callable(_Session))
    container.register(providers.Callable(_Repository))
    container.register(providers.Callable(_Service))
    return container


def test_can_instantiate_context(container: Container) -> None:
    assert container.context()


def test_can_retrieve_service(container: Container) -> None:
    with container.sync_context() as ctx:
        service = ctx.resolve(_Service)
        assert isinstance(service, _Service)
        assert isinstance(service.repository, _Repository)
        assert isinstance(service.repository.session, _Session)


def test_uses_cache(container: Container) -> None:
    with container.sync_context() as ctx:
        service = ctx.resolve(_Service)
        a, b, c = service, service.repository, service.repository.session

        service = ctx.resolve(_Service)
        assert a is service
        assert b is service.repository
        assert c is service.repository.session


def test_does_not_preserve_cache_if_recreated(container: Container) -> None:
    with container.sync_context() as ctx:
        service = ctx.resolve(_Service)

    with container.sync_context() as ctx:
        assert ctx.resolve(_Service) is not service


@pytest.mark.anyio()
async def test_provide_async() -> None:
    class Test:
        pass

    container = Container()
    container.register(Callable(Test))
    async with container.context() as ctx:
        instance = await ctx.resolve(Test)
        assert isinstance(instance, Test)
