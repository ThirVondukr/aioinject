from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends

from benchmark.dependencies import (
    RepositoryA,
    RepositoryB,
    ServiceA,
    ServiceB,
    Session,
    UseCase,
)


async def _get_session() -> AsyncIterator[Session]:
    yield Session()


SessionDepends = Annotated[Session, Depends(_get_session)]


async def _get_repository_a(session: SessionDepends) -> RepositoryA:
    return RepositoryA(session)


RepositoryADepends = Annotated[RepositoryA, Depends(_get_repository_a)]


async def _get_repository_b(session: SessionDepends) -> RepositoryB:
    return RepositoryB(session)


RepositoryBDepends = Annotated[RepositoryB, Depends(_get_repository_b)]


async def _get_service_a(repository_a: RepositoryADepends) -> ServiceA:
    return ServiceA(repository=repository_a)


ServiceADepends = Annotated[ServiceA, Depends(_get_service_a)]


async def _get_service_b(repository_b: RepositoryBDepends) -> ServiceB:
    return ServiceB(repository=repository_b)


ServiceBDepends = Annotated[ServiceB, Depends(_get_service_b)]


async def _get_usecase(
    service_a: ServiceADepends,
    service_b: ServiceBDepends,
) -> UseCase:
    return UseCase(
        service_a=service_a,
        service_b=service_b,
    )


UseCaseDepends = Annotated[UseCase, Depends(_get_usecase)]
