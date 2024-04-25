from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

import aioinject
from aioinject import _utils, decorators
from aioinject._types import P, T


__all__ = ["inject", "AioInjectMiddleware"]


def inject(function: Callable[P, T]) -> Callable[P, T]:
    wrapper = decorators.inject(
        function,
        inject_method=decorators.InjectMethod.context,
    )
    return _utils.clear_wrapper(wrapper)


class AioInjectMiddleware(BaseMiddleware):
    def __init__(self, container: aioinject.Container) -> None:
        self.container = container

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with self.container.context():
            return await handler(event, data)
