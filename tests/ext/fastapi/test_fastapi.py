import contextlib
import uuid
from typing import Any

import httpx
import pytest
from _pytest.fixtures import SubRequest

import aioinject
from aioinject import Scoped, Singleton, Transient
from tests.ext.utils import ExceptionPropagation, PropagatedError


@pytest.fixture(params=["/function-route", "/depends"])
async def route(request: SubRequest) -> str:
    return request.param


async def test_function_route(
    http_client: httpx.AsyncClient,
    provided_value: int,
    route: str,
) -> None:
    response = await http_client.get(route)
    assert response.status_code == httpx.codes.OK.value
    assert response.json() == {"value": provided_value}


async def test_function_route_override(
    http_client: httpx.AsyncClient,
    container: aioinject.Container,
    route: str,
) -> None:
    expected = str(uuid.uuid4())
    with container.override(aioinject.Object(expected, type_=int)):
        response = await http_client.get(route)
    assert response.status_code == httpx.codes.OK.value
    assert response.json() == {"value": expected}


@pytest.mark.parametrize(
    ("provider_type", "should_propagate"),
    [
        (Singleton, False),
        (Scoped, True),
        (Transient, True),
    ],
)
async def test_propagation(
    http_client: httpx.AsyncClient,
    container: aioinject.Container,
    provider_type: Any,
    should_propagate: bool,
) -> None:
    propagation = ExceptionPropagation()

    with (
        container.override(provider_type(propagation.dependency, type_=int)),
        contextlib.suppress(PropagatedError),
    ):
        await http_client.get("/raise-exception")

    if should_propagate:
        assert isinstance(propagation.exc, PropagatedError)
    else:
        assert propagation.exc is None
