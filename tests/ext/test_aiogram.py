from typing import Annotated

from aiogram import Router

from aioinject import Container, Inject, Object
from aioinject.ext.aiogram import AioInjectMiddleware, inject


_NUMBER = 42


async def test_middleware() -> None:
    container = Container()
    container.register(Object(_NUMBER))

    middleware = AioInjectMiddleware(container=container)
    event_ = object()
    data_ = object()

    @inject
    async def handler(
        event: object,
        data: object,
        number: Annotated[int, Inject],
    ) -> None:
        assert event is event_
        assert data is data_
        assert number == _NUMBER

    await middleware(handler=handler, event=event_, data=data_)  # type: ignore[arg-type]


def test_add_to_router() -> None:
    middleware = AioInjectMiddleware(container=Container())

    router = Router()
    middleware.add_to_router(router=router)

    for observer in router.observers.values():
        assert observer.outer_middleware[0] is middleware
