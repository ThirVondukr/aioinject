from typing import Annotated

import pytest

from aioinject import Container, Inject, inject, providers


class _Session:
    pass


class _Service:
    def __init__(self, session: Annotated[_Session, Inject]):
        self.session = session


class _Interface:
    def __init__(self, session: Annotated[_Session, Inject]):
        self.session = session


class _ImplementationA(_Interface):
    pass


class _ImplementationB(_Interface):
    pass


def _get_impl_b(session: Annotated[_Session, Inject]) -> _ImplementationB:
    return _ImplementationB(session)


class _NeedsMultipleImplementations:
    def __init__(
        self,
        a: Annotated[_Interface, Inject(_ImplementationA)],
        b: Annotated[_Interface, Inject(_get_impl_b)],
    ):
        self.a = a
        self.b = b


@pytest.fixture
def container() -> Container:
    container = Container()
    container.register(providers.Callable(_Session))
    container.register(providers.Callable(_Service))
    container.register(providers.Callable(_ImplementationA, type_=_Interface))
    container.register(providers.Callable(_get_impl_b, type_=_Interface))
    container.register(providers.Callable(_NeedsMultipleImplementations))
    return container


@inject
def _injectee(
    test: Annotated[_Session, Inject],
    test_no_cache: Annotated[_Session, Inject(cache=False)],
):
    return test, test_no_cache


def test_would_fail_without_active_context():
    with pytest.raises(TypeError):
        _injectee()


def test_would_not_inject_without_inject_marker(container):
    @inject
    def injectee(test: _Session):
        pass

    with container.sync_context(), pytest.raises(TypeError):
        injectee()


def test_simple_inject(container):
    with container.sync_context():
        session, *_ = _injectee()
        assert isinstance(session, _Session)


def test_no_cache_marker(container):
    with container.sync_context():
        test_first, no_cache_first = _injectee()
        test_second, no_cache_second = _injectee()

    assert test_second is test_second
    assert test_first is not no_cache_first
    assert test_second is not no_cache_second
    assert no_cache_first is not no_cache_second


@pytest.mark.anyio
async def test_simple_service(container):
    with container.sync_context() as ctx:
        session = ctx.resolve(_Session)
        assert isinstance(session, _Session)

    async with container.context() as ctx:
        session = await ctx.resolve(_Session)
        assert isinstance(session, _Session)


@pytest.mark.anyio
async def test_retrieve_service_with_dependencies(container):
    with container.sync_context() as ctx:
        service = ctx.resolve(_Service)
        assert isinstance(service, _Service)
        assert isinstance(service.session, _Session)

    async with container.context() as ctx:
        service = await ctx.resolve(_Service)
        assert isinstance(service, _Service)
        assert isinstance(service.session, _Session)


@pytest.mark.anyio
async def test_service_with_multiple_dependencies_with_same_type(container):
    with container.sync_context() as ctx:
        service = ctx.resolve(_NeedsMultipleImplementations)
        assert isinstance(service.a, _ImplementationA)
        assert isinstance(service.b, _ImplementationB)

    async with container.context() as ctx:
        service = await ctx.resolve(_NeedsMultipleImplementations)
        assert isinstance(service.a, _ImplementationA)
        assert isinstance(service.b, _ImplementationB)
