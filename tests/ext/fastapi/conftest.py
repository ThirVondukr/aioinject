from collections.abc import AsyncIterator
from typing import Annotated

import httpx
import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport

import aioinject
from aioinject import Inject
from aioinject.ext.fastapi import AioInjectMiddleware, inject


@inject
async def dependency(number: Annotated[int, Inject]) -> AsyncIterator[int]:
    yield number


@pytest.fixture
def app(container: aioinject.Container) -> FastAPI:
    app_ = FastAPI()
    app_.add_middleware(AioInjectMiddleware, container=container)

    @app_.get("/function-route")
    @inject
    async def function_route(
        provided: Annotated[int, Inject],
    ) -> dict[str, str | int]:
        return {"value": provided}

    @app_.get("/depends")
    @inject
    async def route_with_depends(
        number: Annotated[int, Depends(dependency)],
    ) -> dict[str, str | int]:
        return {"value": number}

    return app_


@pytest.fixture
async def http_client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=ASGITransport(app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        yield client
