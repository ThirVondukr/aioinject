import uuid

import httpx
import pytest
import strawberry


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


async def test_subscription(
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
    async for res in await schema.subscribe(subscription):
        print(res)