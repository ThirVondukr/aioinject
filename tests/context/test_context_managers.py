import contextlib
from typing import AsyncIterable, Iterable
from unittest.mock import MagicMock

import pytest

from aioinject import Callable, Container, providers
from tests.context.test_context import _Session


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
