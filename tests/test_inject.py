from typing import Annotated, NewType

from aioinject.markers import Injected
import pytest

from aioinject import Container, Inject, Object, Scoped, inject, providers
from aioinject.context import container_var
from aioinject.decorators import InjectMethod


class _Session:
    pass


class _Service:
    def __init__(self, session: _Session) -> None:
        self.session = session


class _Interface:
    def __init__(self, session: _Session) -> None:
        self.session = session


@pytest.fixture
def container() -> Container:
    container = Container()
    container.register(providers.Scoped(_Session))
    container.register(providers.Scoped(_Service))
    return container


@inject
def _injectee(
    test: Annotated[_Session, Inject],
    test_no_cache: Annotated[_Session, Inject()],
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

def test_simple_inject_with_injected(container: Container) -> None:
    @inject
    def injectee(
        test: Injected[_Session],
        test_no_cache: Injected[_Session],
    ) -> tuple[_Session, _Session]:
        return test, test_no_cache

    with container.sync_context():
        session, *_ = _injectee()  # type: ignore[call-arg]
        assert isinstance(session, _Session)

async def test_simple_service(container: Container) -> None:
    with container.sync_context() as ctx:
        session = ctx.resolve(_Session)
        assert isinstance(session, _Session)

    async with container.context() as ctx:
        session = await ctx.resolve(_Session)
        assert isinstance(session, _Session)


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


async def test_new_type() -> None:
    A = NewType("A", int)
    B = NewType("B", int)

    class Service:
        def __init__(self, a: A, b: B) -> None:
            self.a = a
            self.b = b

    container = Container()
    container.register(Object(1, type_=A))
    container.register(Object(2, type_=B))
    container.register(Scoped(Service))

    async with container.context() as ctx:
        service = await ctx.resolve(Service)
        assert service.a == 1
        assert service.b == 2  # noqa: PLR2004
