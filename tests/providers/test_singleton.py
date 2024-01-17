import pytest

from aioinject import Container, Singleton


class _Test:
    pass


@pytest.fixture
def container() -> Container:
    container = Container()
    container.register(Singleton(_Test))
    return container


def test_identity(container: Container) -> None:
    with container.sync_context() as ctx:
        instance = ctx.resolve(_Test)

    with container.sync_context() as ctx:
        assert instance is ctx.resolve(_Test)


@pytest.mark.anyio
async def test_identity_async(container: Container) -> None:
    async with container.context() as ctx:
        instance = await ctx.resolve(_Test)

    async with container.context() as ctx:
        assert instance is await ctx.resolve(_Test)


@pytest.mark.anyio
async def test_should_not_execute_twice() -> None:
    count = 0

    async def func() -> int:
        nonlocal count
        count += 1
        return count

    container = Container()
    container.register(Singleton(func))
    for _ in range(5):
        async with container.context() as ctx:
            assert await ctx.resolve(int) == count
            assert count == 1
