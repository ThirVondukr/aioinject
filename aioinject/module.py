from __future__ import annotations

import inspect
from typing import ClassVar

from .providers import Provider


class Module:
    providers: ClassVar[list[Provider]] = []

    @classmethod
    def __init_subclass__(cls: Module):
        super().__init_subclass__()
        cls.providers = cls.providers.copy()
        cls.providers.extend(
            provider for _, provider
            in inspect.getmembers(cls, Provider.__instancecheck__)
        )

    @classmethod
    def register(cls: Module, provider: Provider):
        cls.providers.append(provider)
