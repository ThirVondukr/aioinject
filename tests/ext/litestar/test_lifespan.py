import contextlib
from collections.abc import AsyncIterator

import pytest
from litestar import Litestar

import aioinject
from aioinject import Container
from aioinject.ext.litestar import AioInjectPlugin


@pytest.mark.anyio
async def test_lifespan() -> None:
    number = 42

    shutdown = False

    @contextlib.asynccontextmanager
    async def dependency() -> AsyncIterator[int]:
        nonlocal shutdown
        yield number
        shutdown = True

    container = Container()
    container.register(aioinject.Singleton(dependency))

    app = Litestar(plugins=[AioInjectPlugin(container)])

    async with app.lifespan():
        async with container.context() as ctx:
            assert await ctx.resolve(int) == number

        assert shutdown is False
    assert shutdown is True
