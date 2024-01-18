import contextlib
from collections.abc import AsyncIterator

import pytest

from aioinject import Container
from aioinject.providers import Transient


class _Test:
    pass


@pytest.fixture
def container() -> Container:
    container = Container()
    container.register(Transient(_Test))
    return container


@pytest.mark.anyio
def test_identity(container: Container) -> None:
    with container.sync_context() as ctx:
        assert ctx.resolve(_Test) is not ctx.resolve(_Test)


@pytest.mark.anyio
async def test_identity_async(container: Container) -> None:
    async with container.context() as ctx:
        assert await ctx.resolve(_Test) is not await ctx.resolve(_Test)


@pytest.mark.anyio
async def test_should_close_transient_dependencies() -> None:
    count = 0

    @contextlib.asynccontextmanager
    async def dependency() -> AsyncIterator[int]:
        nonlocal count
        count += 1
        yield count
        count -= 1

    container = Container()
    container.register(Transient(dependency))

    max_count = 10
    async with container.context() as ctx:
        for i in range(1, max_count + 1):
            assert await ctx.resolve(int) == count == i
        assert count == max_count
    assert count == 0
