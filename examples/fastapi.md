```python
import contextlib
from collections.abc import AsyncIterator
from typing import Annotated

import uvicorn
from fastapi import FastAPI

import aioinject
from aioinject import Inject
from aioinject.ext.fastapi import AioInjectMiddleware, inject

container = aioinject.Container()
container.register(aioinject.Object(42))


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with contextlib.aclosing(container):
        yield


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)

    @app.get("/")
    @inject
    async def root(number: Annotated[int, Inject]) -> int:
        return number

    app.add_middleware(AioInjectMiddleware, container=container)

    return app


if __name__ == "__main__":
    uvicorn.run("main:create_app", factory=True, reload=True)

```
