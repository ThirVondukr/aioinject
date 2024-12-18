import time
from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Annotated

import httpx
import strawberry
from httpx import ASGITransport
from strawberry import Schema
from strawberry.asgi import GraphQL
from strawberry.schema.config import StrawberryConfig

from aioinject import Inject
from aioinject.ext.strawberry import AioInjectExtension, inject
from benchmark.container import create_container
from benchmark.dependencies import (
    RepositoryA,
    RepositoryB,
    ServiceA,
    ServiceB,
    UseCase,
    create_session,
)
from benchmark.dto import BenchmarkResult


@strawberry.type
class Query:
    @strawberry.field
    async def by_hand(self) -> int:
        async with create_session() as session:
            use_case = UseCase(
                service_a=ServiceA(repository=RepositoryA(session=session)),
                service_b=ServiceB(repository=RepositoryB(session=session)),
            )
            return await use_case.execute()

    @strawberry.field
    @inject
    async def aioinject(self, use_case: Annotated[UseCase, Inject]) -> int:
        return await use_case.execute()


async def bench_strawberry(
    iterations: int,
) -> AsyncIterator[BenchmarkResult]:
    schema = Schema(
        query=Query,
        extensions=[AioInjectExtension(create_container())],
        config=StrawberryConfig(auto_camel_case=False),
    )
    app = GraphQL[None, None](schema=schema)

    resolver_names = ["by_hand", "aioinject"]
    query = """
    query { result: RESOLVER_NAME }
    """

    async with httpx.AsyncClient(
        transport=ASGITransport(app),
        base_url="http://test",
    ) as client:
        for resolver_name in resolver_names:
            durations = []
            for _ in range(iterations):
                start = time.perf_counter()
                response = await client.post(
                    "/",
                    json={
                        "query": query.replace("RESOLVER_NAME", resolver_name),
                    },
                )
                durations.append(
                    timedelta(seconds=time.perf_counter() - start),
                )
                response.raise_for_status()
                assert response.json() == {  # noqa: S101
                    "data": {"result": 42},
                }

            yield BenchmarkResult(
                name=f"Strawberry - {resolver_name}",
                durations=durations,
                iterations=iterations,
            )
