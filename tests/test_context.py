import contextlib
from typing import Annotated, Iterable
from unittest.mock import MagicMock

import pytest

from dependency_depression import providers
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
    with container.context() as ctx:
        service = ctx.resolve_sync(_Service)
        assert isinstance(service, _Service)
        assert isinstance(service.repository, _Repository)
        assert isinstance(service.repository.session, _Session)


def test_uses_cache(container):
    with container.context() as ctx:
        service = ctx.resolve_sync(_Service)
        a, b, c = service, service.repository, service.repository.session

        service = ctx.resolve_sync(_Service)
        assert a is service
        assert b is service.repository
        assert c is service.repository.session


def test_does_not_preserve_cache_if_recreated(container):
    with container.context() as ctx:
        service = ctx.resolve_sync(_Service)

    with container.context() as ctx:
        assert ctx.resolve_sync(_Service) is not service


def test_shutdowns_context_manager():
    mock = MagicMock()

    @contextlib.contextmanager
    def get_number() -> Iterable[int]:
        yield 42
        mock.close()

    container = Depression()
    container.register(int, providers.Callable(get_number))

    with container.context() as ctx:
        number = ctx.resolve_sync(int)
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

    with container.context() as ctx:
        ctx.resolve_sync(_Test)
        mock.open.assert_not_called()
    mock.close.assert_not_called()
