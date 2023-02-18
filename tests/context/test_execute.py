from typing import Annotated

import pytest

from aioinject import Inject, Container
from aioinject.providers import collect_dependencies

from .conftest import _A, _C


def _dependant(
    a: Annotated[_A, Inject],
    c: Annotated[_C, Inject],
) -> tuple[_A, _C]:
    return a, c


async def _async_dependant(
    a: Annotated[_A, Inject],
    c: Annotated[_C, Inject],
) -> tuple[_A, _C]:
    return a, c


def test_execute_sync(container: Container) -> None:
    dependencies = list(collect_dependencies(_dependant))
    with container.sync_context() as ctx:
        a, c = ctx.execute(_dependant, dependencies)
        assert isinstance(a, _A)
        assert isinstance(c, _C)


def test_execute_sync_with_kwargs(container: Container) -> None:
    dependencies = list(collect_dependencies(_dependant))
    provided_a = _A()
    with container.sync_context() as ctx:
        a, c = ctx.execute(_dependant, dependencies, a=provided_a)
        assert a is provided_a
        assert isinstance(c, _C)


@pytest.mark.anyio
async def test_execute_async(container: Container) -> None:
    dependencies = list(collect_dependencies(_dependant))
    async with container.context() as ctx:
        a, c = await ctx.execute(_dependant, dependencies)
        assert isinstance(a, _A)
        assert isinstance(c, _C)


@pytest.mark.anyio
async def test_execute_async_with_kwargs(container: Container) -> None:
    dependencies = list(collect_dependencies(_dependant))
    provided_a = _A()
    async with container.context() as ctx:
        a, c = await ctx.execute(_dependant, dependencies, a=provided_a)
        assert isinstance(a, _A)
        assert isinstance(c, _C)


@pytest.mark.anyio
async def test_execute_async_coroutine(container: Container) -> None:
    dependencies = list(collect_dependencies(_async_dependant))
    async with container.context() as ctx:
        a, c = await ctx.execute(_async_dependant, dependencies)
        assert isinstance(a, _A)
        assert isinstance(c, _C)
