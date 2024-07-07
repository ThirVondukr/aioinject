from collections.abc import AsyncIterator
from re import sub
from typing import Any

import httpx
import pytest
from httpx import ASGITransport
from strawberry import Schema
from strawberry.asgi import GraphQL

import aioinject
from aioinject.ext.strawberry import AioInjectExtension
from tests.ext.strawberry.app import StrawberryApp, _Query, _Subscription


@pytest.fixture(autouse=True)
def anyio_backend() -> str:
    return "asyncio"

@pytest.fixture
async def schema(container: aioinject.Container) -> Schema:
    return Schema(
        query=_Query,
        subscription=_Subscription,
        extensions=[AioInjectExtension(container=container)],
    )
@pytest.fixture
async def app(schema: Schema) -> GraphQL[Any, Any]:
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
