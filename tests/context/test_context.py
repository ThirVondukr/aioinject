import contextlib
from collections.abc import AsyncIterator, Generator
from typing import Annotated, Any, Self

import anyio
import pytest

from aioinject import Object, Provider, Scoped, Singleton, providers
from aioinject.containers import Container
from aioinject.markers import Inject


pytestmark = [pytest.mark.anyio]


class _TestError(Exception):
    pass


class _Session:
    pass


class _Repository:
    def __init__(self, session: Annotated[_Session, Inject]) -> None:
        self.session = session


class _Service:
    def __init__(self, repository: Annotated[_Repository, Inject]) -> None:
        self.repository = repository


@pytest.fixture
def container() -> Container:
    container = Container()
    container.register(providers.Scoped(_Session))
    container.register(providers.Scoped(_Repository))
    container.register(providers.Scoped(_Service))
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


async def test_provide_async() -> None:
    class Test:
        pass

    container = Container()
    container.register(Scoped(Test))
    async with container.context() as ctx:
        instance = await ctx.resolve(Test)
        assert isinstance(instance, Test)


class _AwaitableCls:
    def __init__(self) -> None:
        self.awaited = False

    def __await__(self) -> Generator[Any, None, None]:
        self.awaited = True
        return anyio.sleep(0).__await__()


async def _async_awaitable() -> _AwaitableCls:
    return _AwaitableCls()


def _sync_awaitable() -> _AwaitableCls:
    return _AwaitableCls()


@pytest.mark.parametrize(
    "provider",
    [
        Scoped(_async_awaitable),  # type: ignore[arg-type]
        Scoped(_sync_awaitable),  # type: ignore[arg-type]
        Singleton(_async_awaitable),  # type: ignore[arg-type]
        Singleton(_sync_awaitable),  # type: ignore[arg-type]
    ],
)
async def test_should_not_execute_awaitable_classes(
    provider: Provider[_AwaitableCls],
) -> None:
    container = Container()
    container.register(provider)

    async with container.context() as ctx:
        resolved = await ctx.resolve(_AwaitableCls)
        assert isinstance(resolved, _AwaitableCls)
        assert not resolved.awaited


async def test_singleton_contextmanager_error() -> None:
    call_number = 0

    @contextlib.asynccontextmanager
    async def raises_error() -> AsyncIterator[int]:
        nonlocal call_number
        call_number += 1
        if call_number == 1:
            raise _TestError
        yield 42

    container = Container()
    container.register(Singleton(raises_error))

    with pytest.raises(_TestError):
        async with container.context() as ctx:
            await ctx.resolve(int)

    async with container.context() as ctx:
        await ctx.resolve(int)


async def test_returns_self() -> None:
    class Class:
        def __init__(self, number: str) -> None:
            self.number = number

        @classmethod
        async def self_classmethod(cls, number: int) -> Self:
            return cls(number=str(number))

    container = Container()
    container.register(Object(42))
    container.register(Scoped(Class.self_classmethod))

    async with container.context() as ctx:
        instance = await ctx.resolve(Class)
        assert instance.number == "42"
