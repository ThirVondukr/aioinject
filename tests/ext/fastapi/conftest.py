from collections.abc import AsyncIterator
from typing import Annotated

import httpx
import pytest
from fastapi import FastAPI

import aioinject
from aioinject import Inject
from aioinject.ext.fastapi import InjectMiddleware, inject


@pytest.fixture(scope="session")
def provided_value() -> int:
    return 42


@pytest.fixture(scope="session")
def container(provided_value: int) -> aioinject.Container:
    container = aioinject.Container()
    container.register(aioinject.Object(provided_value))
    return container


@pytest.fixture
def app(container: aioinject.Container) -> FastAPI:
    app_ = FastAPI()
    app_.add_middleware(InjectMiddleware, container=container)

    @app_.get("/function-route")
    @inject
    async def function_route(
        provided: Annotated[int, Inject],
    ) -> dict[str, str | int]:
        return {"value": provided}

    return app_


@pytest.fixture
async def http_client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client
