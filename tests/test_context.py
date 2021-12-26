import contextlib
from typing import Annotated, Iterable
from unittest.mock import MagicMock

import pytest

from dependency_depression import Callable, providers
from dependency_depression.containers import Depression
from dependency_depression.markers import Inject


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
    depression = Depression()
    depression.register(_Session, providers.Callable(_Session))
    depression.register(_Repository, providers.Callable(_Repository))
    depression.register(_Service, providers.Callable(_Service))
    return depression


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
    def get_number() -> Iterable[int]:
        yield 42
        mock.close()

    container = Depression()
    container.register(int, providers.Callable(get_number))

    with container.sync_context() as ctx:
        number = ctx.resolve(int)
        assert number == 42
        mock.close.assert_not_called()

    mock.close.assert_called()


def test_should_not_use_resolved_class_as_context_manager():
    mock = MagicMock()

    class _Test:
        def __enter__(self):
            mock.open()

        def __exit__(self, exc_type, exc_val, exc_tb):
            mock.close()

    container = Depression()
    container.register(_Test, providers.Callable(_Test))

    with container.sync_context() as ctx:
        ctx.resolve(_Test)
        mock.open.assert_not_called()
    mock.close.assert_not_called()


@pytest.mark.anyio
async def test_provide_async():
    class Test:
        pass

    container = Depression()
    container.register(Test, Callable(Test))
    async with container.context() as ctx:
        instance = await ctx.resolve(Test)
        assert isinstance(instance, Test)


@pytest.mark.anyio
async def test_async_context_manager():
    mock = MagicMock()

    @contextlib.asynccontextmanager
    async def ctx_async() -> int:
        mock.open()
        yield 42
        mock.close()

    container = Depression()
    container.register(int, Callable(ctx_async))
    async with container.context() as ctx:
        mock.open.assert_not_called()
        instance = await ctx.resolve(int)
        mock.open.assert_called_once()
        assert isinstance(instance, int)
    mock.close.assert_called_once()


@pytest.mark.anyio
async def test_async_context_would_use_sync_context_managers():
    mock = MagicMock()

    @contextlib.contextmanager
    def ctx_sync() -> int:
        mock.open()
        yield 42
        mock.close()

    container = Depression()
    container.register(int, Callable(ctx_sync))
    async with container.context() as ctx:
        mock.open.assert_not_called()
        await ctx.resolve(int)
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

    container = Depression()
    container.register(Test, Callable(Test))
    async with container.context() as ctx:
        instance = await ctx.resolve(Test)
        assert isinstance(instance, Test)
    mock.open.assert_not_called()
    mock.close.assert_not_called()


def test_sync_context_manager_should_receive_exception():
    mock = MagicMock()

    @contextlib.contextmanager
    def get_number() -> Iterable[int]:
        try:
            yield 42
        except Exception:
            mock.exception_happened()

    container = Depression()
    container.register(int, Callable(get_number))

    with pytest.raises(Exception):
        with container.sync_context() as ctx:
            number = ctx.resolve(int)
            assert number == 42
            mock.exception_happened.assert_not_called()
            raise Exception

    mock.exception_happened.asssert_called_once()
