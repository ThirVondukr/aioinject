import contextlib
from collections import defaultdict
from collections.abc import Generator
from typing import Any, TypeVar

from .context import InjectionContext, SyncInjectionContext
from .providers import Provider

_T = TypeVar("_T")
_Providers = dict[type[_T], list[Provider[_T]]]


class Container:
    def __init__(self) -> None:
        self.providers: _Providers = defaultdict(list)
        self._overrides: _Providers = defaultdict(list)

    def register(
        self,
        provider: Provider[_T],
    ) -> None:
        if provider.type not in self.providers:
            self.providers[provider.type] = []

        self.providers[provider.type].append(provider)

    @staticmethod
    def _get_provider(
        providers: _Providers,
        type_: type[_T],
        impl: Any | None = None,
    ) -> Provider[_T] | None:
        type_providers = providers[type_]
        if not type_providers:
            return None

        if impl is None and len(type_providers) == 1:
            return type_providers[0]

        if impl is None:
            raise ValueError(
                f"Multiple providers for type {type_} were found,"
                f"you have to specify implementation using Impl"
                f"argument: Annotated[IService, Inject(Service)]"
            )
        return next((p for p in type_providers if p.impl == impl), None)

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
            raise ValueError(f"Provider for type {type_} not found")
        return provider

    def context(self) -> InjectionContext:
        return InjectionContext(container=self)

    def sync_context(self) -> SyncInjectionContext:
        return SyncInjectionContext(container=self)

    @contextlib.contextmanager
    def override(
        self,
        provider: Provider[_T],
        type_: type[_T] | None = None,
        impl: Any | None = None,
    ) -> Generator[None, None, None]:
        impl = impl or provider.impl

        self._overrides[provider.type].append(provider)
        yield
        self._overrides[provider.type].remove(provider)
