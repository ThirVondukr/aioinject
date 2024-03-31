from __future__ import annotations

import collections.abc
import enum
import functools
import inspect
import typing
from collections.abc import Mapping
from dataclasses import dataclass
from inspect import isclass
from typing import (
    Annotated,
    Any,
    ClassVar,
    Generic,
    Protocol,
    TypeAlias,
    TypeVar,
    runtime_checkable,
)

from typing_extensions import Self

from aioinject._utils import (
    _get_type_hints,
    is_context_manager_function,
    remove_annotation,
)
from aioinject.markers import Inject


_T = TypeVar("_T")


@dataclass(slots=True, kw_only=True, frozen=True)
class Dependency(Generic[_T]):
    name: str
    type_: type[_T]


def _get_annotation_args(type_hint: Any) -> tuple[type, tuple[Any, ...]]:
    try:
        dep_type, *args = typing.get_args(type_hint)
    except ValueError:
        dep_type, args = type_hint, []
    return dep_type, tuple(args)


def _find_inject_marker_in_annotation_args(
    args: tuple[Any, ...],
) -> Inject | None:
    for arg in args:
        try:
            if issubclass(arg, Inject):
                return Inject()
        except TypeError:
            pass

        if isinstance(arg, Inject):
            return arg
    return None


def collect_dependencies(
    dependant: typing.Callable[..., object] | dict[str, Any],
    ctx: dict[str, type[Any]] | None = None,
) -> typing.Iterable[Dependency[object]]:
    if not isinstance(dependant, dict):
        with remove_annotation(dependant.__annotations__, "return"):
            type_hints = _get_type_hints(dependant, context=ctx)
    else:
        type_hints = dependant
    for name, hint in type_hints.items():
        dep_type, args = _get_annotation_args(hint)
        inject_marker = _find_inject_marker_in_annotation_args(args)
        if inject_marker is None:
            continue

        yield Dependency(
            name=name,
            type_=dep_type,
        )


def _typevar_map(
    source: type[Any],
) -> tuple[type, Mapping[object, object]]:
    origin = typing.get_origin(source)
    if not isclass(source) and not origin:
        return source, {}

    resolved_source = origin or source
    typevar_map: dict[object, object] = {}
    for base in (source, *getattr(source, "__orig_bases__", [])):
        origin = typing.get_origin(base)
        if not origin:
            continue

        params = getattr(origin, "__parameters__", ())
        args = typing.get_args(base)
        typevar_map |= dict(zip(params, args, strict=False))

    return resolved_source, typevar_map


def _get_provider_type_hints(
    provider: Provider[Any],
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source, typevar_map = _typevar_map(source=provider.impl)

    if inspect.isclass(source):
        source = source.__init__

    if isinstance(source, functools.partial):
        return {}

    type_hints = _get_type_hints(source, context=context)
    for key, value in type_hints.items():
        _, args = _get_annotation_args(value)
        for arg in args:
            if isinstance(arg, Inject):
                break
        else:
            type_hints[key] = Annotated[typevar_map.get(value, value), Inject]

    return type_hints


_GENERATORS = {
    collections.abc.Generator,
    collections.abc.Iterator,
}
_ASYNC_GENERATORS = {
    collections.abc.AsyncGenerator,
    collections.abc.AsyncIterator,
}

_FactoryType: TypeAlias = (
    type[_T]
    | typing.Callable[..., _T]
    | typing.Callable[..., collections.abc.Awaitable[_T]]
    | typing.Callable[..., collections.abc.Coroutine[Any, Any, _T]]
    | typing.Callable[..., collections.abc.Iterator[_T]]
    | typing.Callable[..., collections.abc.AsyncIterator[_T]]
)


def _guess_return_type(factory: _FactoryType[_T]) -> type[_T]:
    unwrapped = inspect.unwrap(factory)

    origin = typing.get_origin(factory)
    is_generic = origin and isclass(origin)
    if isclass(factory) or is_generic:
        return typing.cast(type[_T], factory)

    type_hints = _get_type_hints(unwrapped)
    try:
        return_type = type_hints["return"]
    except KeyError as e:
        msg = f"Factory {factory.__qualname__} does not specify return type."
        raise ValueError(msg) from e

    if origin := typing.get_origin(return_type):
        args = typing.get_args(return_type)

        is_async_gen = (
            origin in _ASYNC_GENERATORS
            and inspect.isasyncgenfunction(unwrapped)
        )
        is_sync_gen = origin in _GENERATORS and inspect.isgeneratorfunction(
            unwrapped,
        )
        if is_async_gen or is_sync_gen:
            return_type = args[0]

    # Classmethod returning `typing.Self`
    if return_type == Self and (
        self_cls := getattr(factory, "__self__", None)
    ):
        return self_cls

    return return_type


class DependencyLifetime(enum.Enum):
    transient = enum.auto()
    scoped = enum.auto()
    singleton = enum.auto()


@runtime_checkable
class Provider(Protocol[_T]):
    impl: Any
    type_: type[_T]
    lifetime: DependencyLifetime
    _cached_dependencies: tuple[Dependency[object], ...]

    async def provide(self, kwargs: Mapping[str, Any]) -> _T: ...

    def provide_sync(self, kwargs: Mapping[str, Any]) -> _T: ...

    def resolve_dependencies(
        self,
        context: dict[str, Any] | None = None,
    ) -> tuple[Dependency[object], ...]:
        try:
            return self._cached_dependencies
        except AttributeError:
            self._cached_dependencies = tuple(
                collect_dependencies(self.type_hints(context), ctx=context),
            )
            return self._cached_dependencies

    def type_hints(self, context: dict[str, Any] | None) -> dict[str, Any]: ...

    @property
    def is_async(self) -> bool: ...

    @functools.cached_property
    def is_generator(self) -> bool:
        return is_context_manager_function(self.impl)

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.__class__.__qualname__}(type={self.type_}, implementation={self.impl})"


class Scoped(Provider[_T]):
    lifetime = DependencyLifetime.scoped

    def __init__(
        self,
        factory: _FactoryType[_T],
        type_: type[_T] | None = None,
    ) -> None:
        self.impl = factory
        self.type_ = type_ or _guess_return_type(factory)

    def provide_sync(self, kwargs: Mapping[str, Any]) -> _T:
        return self.impl(**kwargs)  # type: ignore[return-value]

    async def provide(self, kwargs: Mapping[str, Any]) -> _T:
        if self.is_async:
            return await self.impl(**kwargs)  # type: ignore[misc]

        return self.provide_sync(kwargs)

    def type_hints(
        self,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        type_hints = _get_provider_type_hints(self, context=context)
        if "return" in type_hints:
            del type_hints["return"]
        return type_hints

    @functools.cached_property
    def is_async(self) -> bool:
        return inspect.iscoroutinefunction(self.impl)


class Singleton(Scoped[_T]):
    lifetime = DependencyLifetime.singleton


class Transient(Scoped[_T]):
    lifetime = DependencyLifetime.transient


class Object(Provider[_T]):
    _type_hints: ClassVar[dict[str, Any]] = {}
    is_async = False
    impl: _T
    lifetime = DependencyLifetime.scoped  # It's ok to cache it

    def __init__(
        self,
        object_: _T,
        type_: type[_T] | None = None,
    ) -> None:
        self.type_ = type_ or type(object_)
        self.impl = object_

    def provide_sync(self, kwargs: Mapping[str, Any]) -> _T:  # noqa: ARG002
        return self.impl

    async def provide(self, kwargs: Mapping[str, Any]) -> _T:  # noqa: ARG002
        return self.impl

    def type_hints(self, _: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._type_hints
