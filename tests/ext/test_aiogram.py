from typing import Annotated

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
