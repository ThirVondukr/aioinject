import asyncio
import functools
from collections.abc import AsyncIterator, Sequence
from datetime import timedelta
from typing import Protocol

from benchmark.benches.fastapi import fastapi_bench
from benchmark.benches.litestar import litestar_bench
from benchmark.benches.python import (
    bench_aioinject_decorator,
    bench_aioinject_raw,
    bench_python,
)
from benchmark.benches.strawberry import bench_strawberry
from benchmark.dto import BenchmarkResult


def time_to_ms(delta: timedelta | float) -> str:
    if isinstance(delta, timedelta):
        delta = delta.total_seconds()
    return f"{delta * 1000:.3f}ms"


def format_result(result: BenchmarkResult, row_template: str) -> str:
    return row_template.format(
        result.name,
        str(result.iterations),
        time_to_ms(sum(result.durations_sec)),
        time_to_ms(result.mean),
        time_to_ms(result.median),
        time_to_ms(result.percentile(0.95)),
        time_to_ms(result.percentile(0.99)),
    )


class BenchFunction(Protocol):
    def __call__(self, iterations: int) -> AsyncIterator[BenchmarkResult]: ...


BENCHMARK_FUNCTIONS: Sequence[BenchFunction] = [
    bench_python,
    bench_aioinject_raw,
    bench_aioinject_decorator,
    functools.partial(
        litestar_bench,
        endpoint="/aioinject",
        enable_aioinject=True,
    ),
    functools.partial(litestar_bench, endpoint="/litestar"),
    functools.partial(fastapi_bench, endpoint="/depends"),
    functools.partial(
        fastapi_bench,
        endpoint="/aioinject",
        enable_aioinject=True,
    ),
    functools.partial(fastapi_bench, endpoint="/by-hand"),
    bench_strawberry,
]


async def main() -> None:
    iterations = [100, 1_000, 10_000]

    row_template = "{:25} {:10} {:10} {:10} {:10} {:10} {:10}"
    print(  # noqa: T201
        row_template.format(
            "Name",
            "iterations",
            "sum",
            "mean",
            "median",
            "p95",
            "p99",
        ),
    )

    for bench_functions in BENCHMARK_FUNCTIONS:
        for count in iterations:
            async for result in bench_functions(iterations=count):
                print(format_result(result, row_template))  # noqa: T201
        print()  # noqa: T201


if __name__ == "__main__":
    asyncio.run(main())
