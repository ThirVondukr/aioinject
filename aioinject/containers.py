import contextlib
from collections import defaultdict
from collections.abc import Iterator
from typing import Any, TypeAlias, TypeVar

from aioinject.context import InjectionContext, SyncInjectionContext
from aioinject.providers import Provider, Singleton


_T = TypeVar("_T")
_Providers: TypeAlias = dict[type[_T], list[Provider[_T]]]


class Container:
    def __init__(self) -> None:
        self.providers: _Providers[Any] = defaultdict(list)
        self._overrides: _Providers[Any] = defaultdict(list)

    def register(
        self,
        provider: Provider[Any],
    ) -> None:
        self.providers[provider.type_].append(provider)

    @staticmethod
    def _get_provider(
        providers: _Providers[_T],
        type_: type[_T],
        impl: Any | None = None,
    ) -> Provider[_T] | None:
        type_providers = providers[type_]
        if not type_providers:
            return None

        if impl is None and len(type_providers) == 1:
            return type_providers[0]

        if impl is None:
            err_msg = (
                f"Multiple providers for type {type_.__qualname__} were found, "
                f"you have to specify implementation using 'impl' parameter: "
                f"Annotated[IService, Inject(impl=Service)]"
            )
            raise ValueError(err_msg)
        return next((p for p in type_providers if p.impl is impl), None)

    def get_provider(
        self,
        type_: type[_T],
        impl: Any | None = None,
    ) -> Provider[_T]:
        overridden_provider = self._get_provider(self._overrides, type_, impl)
        if overridden_provider is not None:
            return overridden_provider

        provider = self._get_provider(self.providers, type_, impl)
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
        self._overrides[provider.type_].append(provider)
        yield
        self._overrides[provider.type_].remove(provider)

    async def aclose(self) -> None:
        for providers in self.providers.values():
            for provider in providers:
                if isinstance(provider, Singleton):
                    await provider.aclose()
