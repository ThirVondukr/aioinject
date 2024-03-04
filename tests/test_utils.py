import contextlib
from collections.abc import AsyncIterator, Iterator
from contextlib import AsyncExitStack, ExitStack

from aioinject._utils import enter_context_maybe, enter_sync_context_maybe


_NUMBER = 42


@contextlib.asynccontextmanager
async def _async_ctx() -> AsyncIterator[int]:
    yield _NUMBER


@contextlib.contextmanager
def _ctx() -> Iterator[int]:
    yield _NUMBER


async def test_enter_context_maybe() -> None:
    for item in (_async_ctx(), _ctx(), _NUMBER):
        assert await enter_context_maybe(item, AsyncExitStack()) == _NUMBER

    for item in (_ctx(), _NUMBER):
        assert enter_sync_context_maybe(item, ExitStack()) == _NUMBER
