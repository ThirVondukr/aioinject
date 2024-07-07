import uuid
from collections.abc import AsyncIterator
from unittest import mock

import httpx
import pytest
import strawberry
from strawberry.types import ExecutionResult

import aioinject
from tests.ext.conftest import ScopedNode


@pytest.mark.parametrize("resolver_name", ["helloWorld", "helloWorldSync"])
async def test_async_resolver(
    http_client: httpx.AsyncClient,
    provided_value: int,
    resolver_name: str,
) -> None:
    query = """
    query($argument: String!) {
        value: RESOLVER_NAME(argument: $argument)
    }
    """.replace(
        "RESOLVER_NAME",
        resolver_name,
    )
    argument = str(uuid.uuid4())
    response = await http_client.post(
        "",
        json={"query": query, "variables": {"argument": argument}},
    )
    assert response.status_code == httpx.codes.OK.value

    assert response.json() == {
        "data": {"value": f"{argument}-{provided_value}"},
    }


async def test_dataloader(
    http_client: httpx.AsyncClient,
) -> None:
    query = """
    query {
        numbers: dataloader
    }
    """
    str(uuid.uuid4())
    response = await http_client.post("", json={"query": query})
    assert response.status_code == httpx.codes.OK.value

    assert response.json() == {
        "data": {"numbers": list(range(100))},
    }


def ensure_agen(
    gen: object,
) -> AsyncIterator[ExecutionResult]:
    if not hasattr(gen, "__aiter__"):
        msg = f"Expected an async generator, got {gen!r}"
        raise TypeError(msg)
    return gen  # type: ignore[return-value]


async def test_subscription(
    container: aioinject.Container,
    schema: strawberry.Schema,
) -> None:
    subscription = """
    subscription {
        liveBars {
            id
            baz
        }
    }
    """
    generate_node_mock = mock.Mock()
    generate_node_mock.return_value = {
        "id": "5986123d250742a681da1defac165b8e",
    }
    provider = container.get_provider(ScopedNode)

    def wrap_mock() -> ScopedNode:
        return generate_node_mock()

    with container.override(provider, aioinject.Scoped(wrap_mock)):
        results = []
        async for res in ensure_agen(await schema.subscribe(subscription)):
            assert res.data
            assert not res.errors
            results.append(res.data["liveBars"])

        assert results == [
            {
                "id": "5986123d250742a681da1defac165b8e",
                "baz": "baz-5986123d250742a681da1defac165b8e",
            }
            for _ in range(5)
        ]
