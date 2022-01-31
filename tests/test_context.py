import contextlib
from typing import Annotated, Iterable, AsyncIterable
from unittest.mock import MagicMock

import pytest

from aioinject import Callable, providers
from aioinject.containers import Container
from aioinject.markers import Inject


class _Session:
    pass


class _Repository:
    def __init__(self, session: Annotated[_Session, Inject]):
        self.session = session


class _Service:
    def __init__(self, repository: Annotated[_Repository, Inject]):
        self.repository = repository


@pytest.fixture
def container():
    container = Container()
    container.register(providers.Callable(_Session))
    container.register(providers.Callable(_Repository))
    container.register(providers.Callable(_Service))
    return container


def test_can_instantiate_context(container):
    assert container.context()


def test_can_retrieve_service(container):
    with container.sync_context() as ctx:
        service = ctx.resolve(_Service)
        assert isinstance(service, _Service)
        assert isinstance(service.repository, _Repository)
        assert isinstance(service.repository.session, _Session)


def test_uses_cache(container):
    with container.sync_context() as ctx:
        service = ctx.resolve(_Service)
        a, b, c = service, service.repository, service.repository.session

        service = ctx.resolve(_Service)
        assert a is service
        assert b is service.repository
        assert c is service.repository.session


def test_does_not_preserve_cache_if_recreated(container):
    with container.sync_context() as ctx:
        service = ctx.resolve(_Service)

    with container.sync_context() as ctx:
        assert ctx.resolve(_Service) is not service


def test_shutdowns_context_manager():
    mock = MagicMock()

    @contextlib.contextmanager
    def get_session() -> Iterable[_Session]:
        yield _Session()
        mock.close()

    container = Container()
    container.register(providers.Callable(get_session))

    with container.sync_context() as ctx:
        session = ctx.resolve(_Session)
        assert isinstance(session, _Session)
        mock.close.assert_not_called()

    mock.close.assert_called()


def test_should_not_use_resolved_class_as_context_manager():
    mock = MagicMock()

    class _Test:
        def __enter__(self):
            mock.open()

        def __exit__(self, exc_type, exc_val, exc_tb):
            mock.close()

    container = Container()
    container.register(providers.Callable(_Test))

    with container.sync_context() as ctx:
        ctx.resolve(_Test)
        mock.open.assert_not_called()
    mock.close.assert_not_called()


@pytest.mark.anyio
async def test_provide_async():
    class Test:
        pass

    container = Container()
    container.register(Callable(Test))
    async with container.context() as ctx:
        instance = await ctx.resolve(Test)
        assert isinstance(instance, Test)


@pytest.mark.anyio
async def test_async_context_manager():
    mock = MagicMock()

    @contextlib.asynccontextmanager
    async def get_session() -> AsyncIterable[_Session]:
        mock.open()
        yield _Session()
        mock.close()

    container = Container()
    container.register(Callable(get_session))
    async with container.context() as ctx:
        mock.open.assert_not_called()
        instance = await ctx.resolve(_Session)
        mock.open.assert_called_once()
        assert isinstance(instance, _Session)
    mock.close.assert_called_once()


@pytest.mark.anyio
async def test_async_context_would_use_sync_context_managers():
    mock = MagicMock()

    @contextlib.contextmanager
    def get_session() -> _Session:
        mock.open()
        yield _Session()
        mock.close()

    container = Container()
    container.register(Callable(get_session))
    async with container.context() as ctx:
        mock.open.assert_not_called()
        await ctx.resolve(_Session)
        mock.open.assert_called_once()
    mock.close.assert_called_once()


@pytest.mark.anyio
async def test_should_not_use_resolved_class_as_async_context_manager():
    mock = MagicMock()

    class Test:
        def __aenter__(self):
            mock.open()

        def __aexit__(self, exc_type, exc_val, exc_tb):
            mock.close()

    container = Container()
    container.register(Callable(Test))
    async with container.context() as ctx:
        instance = await ctx.resolve(Test)
        assert isinstance(instance, Test)
    mock.open.assert_not_called()
    mock.close.assert_not_called()


def test_sync_context_manager_should_receive_exception():
    mock = MagicMock()

    @contextlib.contextmanager
    def get_session() -> Iterable[_Session]:
        try:
            yield 42
        except Exception:
            mock.exception_happened()

    container = Container()
    container.register(Callable(get_session))

    with pytest.raises(Exception):
        with container.sync_context() as ctx:
            session = ctx.resolve(_Session)
            assert isinstance(session, _Session)
            mock.exception_happened.assert_not_called()
            raise Exception

    mock.exception_happened.asssert_called_once()
