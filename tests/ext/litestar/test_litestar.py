import uuid

import httpx
import pytest

import aioinject


@pytest.mark.anyio
async def test_function_route(
    http_client: httpx.AsyncClient,
    provided_value: int,
) -> None:
    response = await http_client.get("/function-route")
    assert response.status_code == httpx.codes.OK.value
    assert response.json() == {"value": provided_value}


@pytest.mark.anyio
async def test_function_route_override(
    http_client: httpx.AsyncClient,
    container: aioinject.Container,
) -> None:
    expected = str(uuid.uuid4())
    with container.override(aioinject.Object(expected, type_=int)):
        response = await http_client.get("/function-route")
    assert response.status_code == httpx.codes.OK.value
    assert response.json() == {"value": expected}
