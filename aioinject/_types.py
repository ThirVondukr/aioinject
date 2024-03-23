from typing import TYPE_CHECKING, TypeAlias, TypeVar, Union


if TYPE_CHECKING:
    from aioinject import InjectionContext, Provider, SyncInjectionContext

T = TypeVar("T")
Providers: TypeAlias = dict[type[T], "Provider[T]"]
AnyCtx: TypeAlias = Union["InjectionContext", "SyncInjectionContext"]
