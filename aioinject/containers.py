from typing import Any, Optional, Type, TypeVar

from .context import InjectionContext, SyncInjectionContext
from .providers import Provider

_T = TypeVar("_T")
_Providers = dict[Type[_T], list[Provider[_T]]]


class Container:
    def __init__(self):
        self.providers: _Providers = {}

    def register(
        self,
        provider: Provider[_T],
    ) -> None:
        if provider.type not in self.providers:
            self.providers[provider.type] = []

        self.providers[provider.type].append(provider)

    def get_provider(
        self,
        type_: Type[_T],
        impl: Optional[Any] = None,
    ) -> Provider[_T]:
        providers = self.providers[type_]
        if impl is None and len(providers) == 1:
            return providers[0]

        if impl is None:
            raise ValueError(
                f"Multiple providers for type {type_} were found,"
                f"you have to specify implementation using Impl"
                f"argument: Annotated[IService, Inject(Service)]"
            )
        return next(p for p in providers if p.impl == impl)

    def context(self) -> InjectionContext:
        return InjectionContext(container=self)

    def sync_context(self) -> SyncInjectionContext:
        return SyncInjectionContext(self)
