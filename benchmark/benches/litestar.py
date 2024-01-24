import time
from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Annotated

import httpx
from litestar import Litestar, get
from litestar.di import Provide
from litestar.logging import LoggingConfig

from aioinject import Inject
from aioinject.ext.fastapi import inject
from aioinject.ext.litestar import AioInjectPlugin
from benchmark.container import create_container
from benchmark.dependencies import (
    RepositoryA,
    RepositoryB,
    ServiceA,
    ServiceB,
    Session,
    UseCase,
)
from benchmark.dto import BenchmarkResult


async def _get_session() -> AsyncIterator[Session]:
    yield Session()


async def _get_repository_a(session: Session) -> RepositoryA:
    return RepositoryA(session)


async def _get_repository_b(session: Session) -> RepositoryB:
    return RepositoryB(session)


async def _get_service_a(repository_a: RepositoryA) -> ServiceA:
    return ServiceA(repository=repository_a)


async def _get_service_b(repository_b: RepositoryB) -> ServiceB:
    return ServiceB(repository=repository_b)


async def _get_usecase(
    service_a: ServiceA,
    service_b: ServiceB,
) -> UseCase:
    return UseCase(
        service_a=service_a,
        service_b=service_b,
    )


@get("/aioinject")
@inject
async def test_aioinject(use_case: Annotated[UseCase, Inject]) -> int:
    return await use_case.execute()


@get("/litestar")
async def test_litestar(use_case: UseCase) -> int:
    return await use_case.execute()


async def litestar_bench(
    iterations: int,
    endpoint: str,
    *,
    enable_aioinject: bool = False,
) -> AsyncIterator[BenchmarkResult]:
    app = Litestar(
        plugins=[AioInjectPlugin(container=create_container())]
        if enable_aioinject
        else [],
        route_handlers=[test_aioinject, test_litestar],
        dependencies={
            "session": Provide(_get_session),
            "repository_a": Provide(_get_repository_a),
            "repository_b": Provide(_get_repository_b),
            "service_a": Provide(_get_service_a),
            "service_b": Provide(_get_service_b),
            "use_case": Provide(_get_usecase),
        },
        logging_config=LoggingConfig(disable_existing_loggers=True),
    )

    durations = []
    async with httpx.AsyncClient(
        app=app,
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
        name=f"Litestar - {endpoint}",
        durations=durations,
        iterations=iterations,
    )
