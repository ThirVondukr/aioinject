from typing import Annotated

import pytest

from dependency_depression import Callable, Depression, Inject, NoCache, inject, providers


class _Test:
    pass


@pytest.fixture
def container():
    depression = Depression()
    depression.register(Callable(_Test))
    return depression


@inject
def _injectee(
    test: Annotated[_Test, Inject],
    test_no_cache: Annotated[_Test, Inject, NoCache],
):
    return test, test_no_cache


def test_would_fail_without_active_context():
    with pytest.raises(TypeError):
        _injectee()


def test_would_not_inject_without_inject_marker(container):
    @inject
    def injectee(test: _Test):
        pass

    with container.sync_context(), pytest.raises(TypeError):
        injectee()


def test_simple_inject(container):
    with container.sync_context():
        test, *_ = _injectee()
        assert isinstance(test, _Test)


def test_no_cache_marker(container):
    with container.sync_context():
        test_first, no_cache_first = _injectee()
        test_second, no_cache_second = _injectee()

    assert test_second is test_second
    assert test_first is not no_cache_first
    assert test_second is not no_cache_second
    assert no_cache_first is not no_cache_second


def test_inject_concrete_implementation():
    class Session:
        pass

    def get_session() -> Session:
        return Session()

    class Service:
        def __init__(
            self,
            # If you don't care how session is created you can leave `Inject` empty
            session: Annotated[Session, Inject],
        ):
            pass

    @inject
    def injectee(
        service: Annotated[Service, Inject],
        # Alternatively you can pass an implementation into Inject
        session: Annotated[Session, Inject[get_session]],
    ):
        return service, session

    container = Depression()
    container.register(providers.Callable(get_session))
    container.register(providers.Callable(Service))

    with container.sync_context() as ctx:
        service, session = injectee()
        assert isinstance(service, Service)
        assert isinstance(session, Session)
