import time
from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Annotated

from aioinject import Inject, inject
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


async def bench_aioinject_raw(
    iterations: int,
) -> AsyncIterator[BenchmarkResult]:
    container = create_container()
    durations = []
    for _ in range(iterations):
        start = time.perf_counter()
        async with container.context() as ctx:
            use_case = await ctx.resolve(UseCase)
            assert use_case

        durations.append(
            timedelta(seconds=time.perf_counter() - start),
        )
    yield BenchmarkResult(
        iterations=iterations,
        durations=durations,
        name="Aioinject",
    )


async def bench_aioinject_decorator(
    iterations: int,
) -> AsyncIterator[BenchmarkResult]:
    container = create_container()

    durations = []

    @inject
    async def injectee(use_case: Annotated[UseCase, Inject]) -> None:
        assert use_case

    for _ in range(iterations):
        start = time.perf_counter()
        async with container.context():
            await injectee()  # type: ignore[call-arg]
        durations.append(
            timedelta(seconds=time.perf_counter() - start),
        )
    yield BenchmarkResult(
        iterations=iterations,
        durations=durations,
        name="Aioinject - Decorator",
    )


async def bench_python(iterations: int) -> AsyncIterator[BenchmarkResult]:
    durations = []
    for _ in range(iterations):
        start = time.perf_counter()
        async with create_session() as session:
            use_case = UseCase(
                service_a=ServiceA(repository=RepositoryA(session=session)),
                service_b=ServiceB(repository=RepositoryB(session=session)),
            )
            assert use_case
        durations.append(
            timedelta(seconds=time.perf_counter() - start),
        )
    yield BenchmarkResult(
        iterations=iterations,
        durations=durations,
        name="Python",
    )
