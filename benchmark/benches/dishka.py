import time
from collections.abc import AsyncIterator
from datetime import timedelta

from dishka import Provider, Scope, make_async_container

from benchmark.dependencies import (
    RepositoryA,
    RepositoryB,
    ServiceA,
    ServiceB,
    UseCase,
    create_session_fastapi,
)
from benchmark.dto import BenchmarkResult


async def bench_dishka(
    iterations: int,
) -> AsyncIterator[BenchmarkResult]:
    provider = Provider(scope=Scope.REQUEST)
    provider.provide(create_session_fastapi)
    provider.provide(RepositoryA)
    provider.provide(RepositoryB)
    provider.provide(ServiceA)
    provider.provide(ServiceB)
    provider.provide(UseCase)
    container = make_async_container(provider)

    durations = []
    for _ in range(iterations):
        start = time.perf_counter()
        async with container() as ctx:
            use_case = await ctx.get(UseCase)
            await use_case.execute()

        durations.append(
            timedelta(seconds=time.perf_counter() - start),
        )
    yield BenchmarkResult(
        iterations=iterations,
        durations=durations,
        name="Dishka",
    )
