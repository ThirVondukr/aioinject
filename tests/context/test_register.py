import aioinject
from aioinject import Object, Scoped


async def test_ok() -> None:
    container = aioinject.Container()
    async with container.context() as ctx:
        ctx.register(Scoped(int))
        assert await ctx.resolve(int) == 0


async def test_should_override_container_provider() -> None:
    value = 42
    container = aioinject.Container()
    container.register(Object(value))

    async with container.context() as ctx:
        assert await ctx.resolve(int) == value

    async with container.context() as ctx:
        ctx.register(Scoped(int))
        assert await ctx.resolve(int) == 0
