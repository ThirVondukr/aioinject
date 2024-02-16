from typing import Annotated

import uvicorn
from litestar import Litestar, get

import aioinject
from aioinject import Inject
from aioinject.ext.litestar import AioInjectPlugin, inject


container = aioinject.Container()
container.register(aioinject.Object(42))


@get("/")
@inject
async def function_route(
    number: Annotated[int, Inject],
) -> int:
    return number


def create_app() -> Litestar:
    return Litestar(
        [function_route],
        plugins=[AioInjectPlugin(container=container)],
    )


if __name__ == "__main__":
    uvicorn.run("main:create_app", factory=True, reload=True)
