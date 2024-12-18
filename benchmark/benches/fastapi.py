import time
from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, FastAPI
from httpx import ASGITransport

from aioinject import Inject
from aioinject.ext.fastapi import AioInjectMiddleware, inject
from benchmark.benches._common import UseCaseDepends
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


router = APIRouter()


@router.get("/aioinject")
@inject
async def test_aioinject(use_case: Annotated[UseCase, Inject]) -> int:
    return await use_case.execute()


@router.get("/depends")
async def test_depends(use_case: Annotated[UseCase, Depends()]) -> int:
    return await use_case.execute()


@router.get("/depends-wrap-async")
async def test_depends_wrap_async(use_case: UseCaseDepends) -> int:
    return await use_case.execute()


@router.get("/by-hand")
async def test_by_hand() -> int:
    async with create_session() as session:
        use_case = UseCase(
            service_a=ServiceA(repository=RepositoryA(session=session)),
            service_b=ServiceB(repository=RepositoryB(session=session)),
        )

    return await use_case.execute()


async def fastapi_bench(
    iterations: int,
    endpoint: str,
    *,
    enable_aioinject: bool = False,
) -> AsyncIterator[BenchmarkResult]:
    app = FastAPI()
    if enable_aioinject:
        app.add_middleware(AioInjectMiddleware, container=create_container())

    app.include_router(router)

    durations = []
    async with httpx.AsyncClient(
        transport=ASGITransport(app),
        base_url="http://test",
    ) as client:
        for _ in range(iterations):
            start = time.perf_counter()
            response = await client.get(endpoint)
            durations.append(
                timedelta(seconds=time.perf_counter() - start),
            )
            response.raise_for_status()
            assert response.content == b"42"  # noqa: S101

    yield BenchmarkResult(
        name=f"FastAPI - {endpoint}",
        durations=durations,
        iterations=iterations,
    )
