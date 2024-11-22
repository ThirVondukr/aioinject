import contextlib
import uuid

import httpx
import pytest

import aioinject
from aioinject import Provider, Scoped, Singleton, Transient
from tests.ext.utils import ExceptionPropagation, PropagatedError


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


@pytest.mark.parametrize(
    ("provider_type", "should_propagate"),
    [
        (Singleton, False),
        (Scoped, True),
        (Transient, True),
    ],
)
async def test_should_propagate_exceptions(
    http_client: httpx.AsyncClient,
    container: aioinject.Container,
    provider_type: type[Provider[int]],
    should_propagate: bool,
) -> None:
    propagation = ExceptionPropagation()

    with (
        container.override(provider_type(propagation.dependency)),  # type: ignore[call-arg]
        contextlib.suppress(PropagatedError),
    ):
        await http_client.get("/raise-exception")

    if should_propagate:
        assert isinstance(propagation.exc, PropagatedError)
    else:
        assert propagation.exc is None
