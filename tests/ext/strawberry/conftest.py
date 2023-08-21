from collections.abc import AsyncIterator
from typing import Annotated, Any

import httpx
import pytest
import strawberry
from strawberry import Schema
from strawberry.asgi import GraphQL

import aioinject
from aioinject import Inject
from aioinject.ext.strawberry import ContainerExtension, inject


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@strawberry.type
class _Query:
    @strawberry.field
    @inject
    async def hello_world(
        self,
        argument: str,
        provided_value: Annotated[int, Inject],
    ) -> str:
        return f"{argument}-{provided_value}"

    @strawberry.field
    @inject
    def hello_world_sync(
        self,
        argument: str,
        provided_value: Annotated[int, Inject],
    ) -> str:
        return f"{argument}-{provided_value}"


@pytest.fixture
async def app(container: aioinject.Container) -> GraphQL[Any, Any]:
    schema = Schema(
        query=_Query,
        extensions=[ContainerExtension(container=container)],
    )
    return GraphQL(schema=schema)


@pytest.fixture
async def http_client(
    app: GraphQL[Any, Any],
) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client
