import contextlib
from collections.abc import AsyncIterator, Iterator
from typing import Literal

import pytest

from aioinject import Object
from aioinject._store import InstanceStore, SingletonStore


pytestmark = [pytest.mark.anyio]

_NUMBER = 42


async def test_async_close() -> None:
    state: Literal["open", "closed"] | None = None

    @contextlib.asynccontextmanager
    async def ctx() -> AsyncIterator[int]:
        nonlocal state
        state = "open"
        yield _NUMBER
        state = "closed"

    store = InstanceStore()
    assert await store.enter_context(ctx()) == _NUMBER
    assert state == "open"

    store.close()
    assert state == "open"

    await store.aclose()
    assert state == "closed"  # type: ignore[comparison-overlap]


async def test_sync_close() -> None:
    state: Literal["open", "closed"] | None = None

    @contextlib.contextmanager
    def ctx() -> Iterator[int]:
        nonlocal state
        state = "open"
        yield _NUMBER
        state = "closed"

    store = InstanceStore()
    assert store.enter_sync_context(ctx()) == _NUMBER
    assert state == "open"

    await store.aclose()
    assert state == "open"

    store.close()
    assert state == "closed"  # type: ignore[comparison-overlap]


@pytest.mark.parametrize(
    "store_cls",
    [InstanceStore, SingletonStore],
)
async def test_lock(store_cls: type[InstanceStore]) -> None:
    store = store_cls()

    provider = Object(0)

    async with store.lock(provider) as should_provide:
        assert should_provide is True

    with store.sync_lock(provider) as should_provide:
        assert should_provide is True

    store.add(provider, 0)

    async with store.lock(provider) as should_provide:
        assert should_provide is False

    with store.sync_lock(provider) as should_provide:
        assert should_provide is False
