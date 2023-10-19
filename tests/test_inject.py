from typing import Annotated

import pytest

from aioinject import Container, Inject, inject, providers
from aioinject.context import container_var
from aioinject.decorators import InjectMethod


class _Session:
    pass


class _Service:
    def __init__(self, session: Annotated[_Session, Inject]) -> None:
        self.session = session


class _Interface:
    def __init__(self, session: Annotated[_Session, Inject]) -> None:
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
    ) -> None:
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
) -> tuple[_Session, _Session]:
    return test, test_no_cache


def test_would_fail_without_active_context() -> None:
    with pytest.raises(LookupError):
        _injectee()  # type: ignore[call-arg]


def test_would_not_inject_without_inject_marker(container: Container) -> None:
    @inject
    def injectee(session: _Session) -> _Session:
        return session

    with container.sync_context(), pytest.raises(TypeError):
        injectee()  # type: ignore[call-arg]


def test_simple_inject(container: Container) -> None:
    with container.sync_context():
        session, *_ = _injectee()  # type: ignore[call-arg]
        assert isinstance(session, _Session)


def test_no_cache_marker(container: Container) -> None:
    with container.sync_context():
        test_first, no_cache_first = _injectee()  # type: ignore[call-arg]
        test_second, no_cache_second = _injectee()  # type: ignore[call-arg]

    assert test_first is test_second
    assert test_first is not no_cache_first
    assert test_second is not no_cache_second
    assert no_cache_first is not no_cache_second


@pytest.mark.anyio
async def test_simple_service(container: Container) -> None:
    with container.sync_context() as ctx:
        session = ctx.resolve(_Session)
        assert isinstance(session, _Session)

    async with container.context() as ctx:
        session = await ctx.resolve(_Session)
        assert isinstance(session, _Session)


@pytest.mark.anyio
async def test_retrieve_service_with_dependencies(
    container: Container,
) -> None:
    with container.sync_context() as ctx:
        service = ctx.resolve(_Service)
        assert isinstance(service, _Service)
        assert isinstance(service.session, _Session)

    async with container.context() as ctx:
        service = await ctx.resolve(_Service)
        assert isinstance(service, _Service)
        assert isinstance(service.session, _Session)


@pytest.mark.anyio
async def test_service_with_multiple_dependencies_with_same_type(
    container: Container,
) -> None:
    with container.sync_context() as ctx:
        service = ctx.resolve(_NeedsMultipleImplementations)
        assert isinstance(service.a, _ImplementationA)
        assert isinstance(service.b, _ImplementationB)

    async with container.context() as ctx:
        service = await ctx.resolve(_NeedsMultipleImplementations)
        assert isinstance(service.a, _ImplementationA)
        assert isinstance(service.b, _ImplementationB)


@pytest.mark.anyio
async def test_inject_using_container(
    container: Container,
) -> None:
    @inject(inject_method=InjectMethod.container)
    async def injectee(service: Annotated[_Service, Inject]) -> _Service:
        return service

    token = container_var.set(container)
    # This is fine
    coro = injectee()  # type: ignore[call-arg]
    assert isinstance(await coro, _Service)
    container_var.reset(token)
