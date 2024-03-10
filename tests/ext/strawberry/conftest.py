from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from httpx import ASGITransport
from strawberry import Schema
from strawberry.asgi import GraphQL

import aioinject
from aioinject.ext.strawberry import AioInjectExtension
from tests.ext.strawberry.app import StrawberryApp, _Query


@pytest.fixture(autouse=True)
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def app(container: aioinject.Container) -> GraphQL[Any, Any]:
    schema = Schema(
        query=_Query,
        extensions=[AioInjectExtension(container=container)],
    )
    return StrawberryApp(schema=schema)


@pytest.fixture
async def http_client(
    app: GraphQL[Any, Any],
) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=ASGITransport(app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        yield client
