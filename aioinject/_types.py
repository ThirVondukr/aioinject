from typing import TYPE_CHECKING, ParamSpec, TypeAlias, TypeVar, Union


if TYPE_CHECKING:
    from aioinject import InjectionContext, Provider, SyncInjectionContext

P = ParamSpec("P")
T = TypeVar("T")
Providers: TypeAlias = dict[type[T], "Provider[T]"]
AnyCtx: TypeAlias = Union["InjectionContext", "SyncInjectionContext"]
Namespace: TypeAlias = dict[str, object]
