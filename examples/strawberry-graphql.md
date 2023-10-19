```python
from typing import Annotated

import strawberry
import uvicorn
from strawberry import Schema
from strawberry.asgi import GraphQL

import aioinject
from aioinject import Inject
from aioinject.ext.strawberry import AioInjectExtension, inject

container = aioinject.Container()
container.register(aioinject.Object(42))


@strawberry.type
class Query:
    @strawberry.field
    @inject
    async def number(self, number: Annotated[int, Inject]) -> int:
        return number


def create_app() -> GraphQL:
    schema = Schema(
        query=Query,
        extensions=[
            AioInjectExtension(container=container),
        ],
    )
    return GraphQL(schema=schema)


if __name__ == "__main__":
    uvicorn.run("main:create_app", factory=True, reload=True)

```
