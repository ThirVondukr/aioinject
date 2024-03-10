from collections.abc import AsyncIterator
from typing import Annotated

import httpx
import pytest
from httpx import ASGITransport
from litestar import Litestar, get

import aioinject
from aioinject import Inject
from aioinject.ext.litestar import AioInjectPlugin, inject


@pytest.fixture
def app(container: aioinject.Container) -> Litestar:
    @get("/function-route")
    @inject
    async def function_route(
        provided: Annotated[int, Inject],
    ) -> dict[str, str | int]:
        return {"value": provided}

    return Litestar(
        [function_route],
        plugins=[AioInjectPlugin(container=container)],
    )


@pytest.fixture
async def http_client(app: Litestar) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=ASGITransport(app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        yield client
