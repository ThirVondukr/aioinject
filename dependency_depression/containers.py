from typing import Any, Optional, Type, TypeVar

from .context import DepressionContext, SyncDepressionContext
from .providers import Provider

_T = TypeVar("_T")
_Providers = dict[Type[_T], list[Provider[_T]]]


class Depression:
    def __init__(self):
        self.providers: _Providers = {}

    def register(self, type_: Type[_T], provider: Provider[_T]) -> None:
        if type_ not in self.providers:
            self.providers[type_] = []

        self.providers[type_].append(provider)

    def get_provider(
        self,
        interface: Type[_T],
        impl: Optional[Any] = None,
    ) -> Provider[_T]:
        providers = self.providers[interface]
        if impl is None and len(providers) == 1:
            return providers[0]

        if impl is None:
            raise ValueError(
                f"Multiple providers for type {interface} were found,"
                f"you have to specify implementation using Impl"
                f"argument: Annotated[IService, Inject, Impl[Service]]"
            )
        return next(p for p in providers if p.impl == impl)

    def context(self) -> DepressionContext:
        return DepressionContext(container=self)

    def sync_context(self) -> SyncDepressionContext:
        return SyncDepressionContext(self)
