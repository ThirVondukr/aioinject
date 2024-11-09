from __future__ import annotations

import dataclasses
from collections.abc import AsyncGenerator, Sequence
from typing import Annotated, Any

import strawberry
from starlette.requests import Request
from starlette.responses import Response
from starlette.websockets import WebSocket
from strawberry.asgi import GraphQL
from strawberry.dataloader import DataLoader
from strawberry.types import Info

from aioinject import Inject
from aioinject.ext.strawberry import inject
from tests.ext.conftest import NumberService, ScopedNode


any_: Any = object()


@strawberry.type
class _Query:
    @strawberry.field
    @inject
    async def hello_world(
        self,
        argument: str,
        provided_value: Annotated[int, Inject],
    ) -> str:
        return f"{argument}-{provided_value}"

    @strawberry.field
    @inject
    def hello_world_sync(
        self,
        argument: str,
        provided_value: Annotated[int, Inject],
    ) -> str:
        return f"{argument}-{provided_value}"

    @strawberry.field
    async def dataloader(self, info: Info[Any, None]) -> Sequence[int]:
        return await info.context.numbers.load_many(list(range(100)))


@strawberry.type
class Bar:
    id: str

    @strawberry.field
    @inject
    def baz(self, scoped_node: Annotated[ScopedNode, Inject]) -> str:
        return f"baz-{scoped_node['id']}"


@strawberry.type
class _Subscription:
    @strawberry.subscription
    @inject
    async def live_bars(
        self,
        node: Annotated[ScopedNode, Inject],
    ) -> AsyncGenerator[Bar, None]:
        for _ in range(5):
            yield Bar(id=node["id"])


@inject
async def load_numbers(
    keys: Sequence[int],
    service: Annotated[NumberService, Inject] = any_,
) -> Sequence[int]:
    return [await service.get_number(key) for key in keys]


@dataclasses.dataclass(slots=True, frozen=True)
class Context:
    request: Request | WebSocket
    response: Response | WebSocket

    numbers: DataLoader[int, int] = dataclasses.field(
        default_factory=lambda: DataLoader(load_numbers),
    )


class StrawberryApp(GraphQL[Context, None]):
    async def get_context(
        self,
        request: Request | WebSocket,
        response: Response | WebSocket,
    ) -> Context:
        return Context(
            request=request,
            response=response,
        )
