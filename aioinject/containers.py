import contextlib
from collections.abc import Iterator
from typing import Any, TypeAlias, TypeVar

from aioinject.context import InjectionContext, SyncInjectionContext
from aioinject.providers import Provider, Singleton


_T = TypeVar("_T")
_Providers: TypeAlias = dict[type[_T], Provider[_T]]


class Container:
    def __init__(self) -> None:
        self.providers: _Providers[Any] = {}
        self._overrides: _Providers[Any] = {}

    def register(
        self,
        provider: Provider[Any],
    ) -> None:
        if provider.type_ in self.providers:
            msg = f"Provider for type {provider.type_} is already registered"
            raise ValueError(msg)

        self.providers[provider.type_] = provider

    def get_provider(self, type_: type[_T]) -> Provider[_T]:
        if (overridden_provider := self._overrides.get(type_)) is not None:
            return overridden_provider

        provider = self.providers.get(type_)
        if provider is None:
            err_msg = f"Provider for type {type_.__qualname__} not found"
            raise ValueError(err_msg)
        return provider

    def context(self) -> InjectionContext:
        return InjectionContext(container=self)

    def sync_context(self) -> SyncInjectionContext:
        return SyncInjectionContext(container=self)

    @contextlib.contextmanager
    def override(
        self,
        provider: Provider[Any],
    ) -> Iterator[None]:
        previous = self._overrides.get(provider.type_)
        self._overrides[provider.type_] = provider

        yield

        del self._overrides[provider.type_]
        if previous is not None:
            self._overrides[provider.type_] = previous

    async def aclose(self) -> None:
        for provider in self.providers.values():
            if isinstance(provider, Singleton):
                await provider.aclose()
