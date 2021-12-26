from typing import Annotated

import pytest

from dependency_depression import inject, Inject, Depression, Callable, NoCache


class _Test:
    pass


@pytest.fixture
def container():
    depression = Depression()
    depression.register(_Test, Callable(_Test))
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
