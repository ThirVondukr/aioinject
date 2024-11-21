import contextlib
import uuid
from collections.abc import AsyncIterator

import httpx

import aioinject
from aioinject import Scoped


async def test_function_route(
    http_client: httpx.AsyncClient,
    provided_value: int,
) -> None:
    response = await http_client.get("/function-route")
    assert response.status_code == httpx.codes.OK.value
    assert response.json() == {"value": provided_value}


async def test_function_route_override(
    http_client: httpx.AsyncClient,
    container: aioinject.Container,
) -> None:
    expected = str(uuid.uuid4())
    with container.override(aioinject.Object(expected, type_=int)):
        response = await http_client.get("/function-route")
    assert response.status_code == httpx.codes.OK.value
    assert response.json() == {"value": expected}


async def test_should_propagate_exceptions(
    http_client: httpx.AsyncClient,
    container: aioinject.Container,
) -> None:
    exc = None

    @contextlib.asynccontextmanager
    async def dependency() -> AsyncIterator[int]:
        nonlocal exc
        try:
            yield 0
        except Exception as e:
            exc = e
            raise

    with (
        container.override(Scoped(dependency)),
        contextlib.suppress(Exception),
    ):
        await http_client.get("/raise-exception")

    assert type(exc) is Exception
    assert str(exc) == "Raised Exception"
