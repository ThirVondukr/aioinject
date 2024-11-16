import time
from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Annotated

import httpx
from httpx import ASGITransport
from litestar import Litestar, get
from litestar.di import Provide
from litestar.logging import LoggingConfig

from aioinject import Inject
from aioinject.ext.fastapi import inject
from aioinject.ext.litestar import AioInjectPlugin
from benchmark.benches._common import (
    _get_repository_a,
    _get_repository_b,
    _get_service_a,
    _get_service_b,
    _get_session,
    _get_usecase,
)
from benchmark.container import create_container
from benchmark.dependencies import (
    UseCase,
)
from benchmark.dto import BenchmarkResult


@get("/aioinject")
@inject
async def test_aioinject(use_case: Annotated[UseCase, Inject]) -> None:
    assert use_case


@get("/litestar")
async def test_litestar(use_case: UseCase) -> None:
    assert use_case


async def litestar_bench(
    iterations: int,
    endpoint: str,
    *,
    enable_aioinject: bool = False,
) -> AsyncIterator[BenchmarkResult]:
    app = Litestar(
        plugins=(
            [AioInjectPlugin(container=create_container())]
            if enable_aioinject
            else []
        ),
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
        transport=ASGITransport(app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        for _ in range(iterations):
            start = time.perf_counter()
            response = await client.get(endpoint)
            durations.append(
                timedelta(seconds=time.perf_counter() - start),
            )
            response.raise_for_status()
            assert response.content == b"null"

    yield BenchmarkResult(
        name=f"Litestar - {endpoint}",
        durations=durations,
        iterations=iterations,
    )
