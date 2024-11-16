from __future__ import annotations

import collections.abc
import dataclasses
import enum
import inspect
import typing
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from inspect import isclass
from typing import (
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
    get_fn_ns,
    get_return_annotation,
    is_context_manager_function,
    remove_annotation,
)
from aioinject.extensions import Extension, SupportsDependencyExtraction
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
    if not isclass(source) and not origin:  # type: ignore[unreachable]  # It's reachable
        return source, {}  # type: ignore[unreachable]

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


def _guess_return_type(factory: _FactoryType[_T]) -> type[_T]:  # noqa: C901
    unwrapped = inspect.unwrap(factory)

    origin = typing.get_origin(factory)
    is_generic = origin and isclass(origin)
    if isclass(factory) or is_generic:
        return typing.cast(type[_T], factory)

    try:
        return_type = _get_type_hints(unwrapped)["return"]
    except KeyError as e:
        msg = f"Factory {factory.__qualname__} does not specify return type."
        raise ValueError(msg) from e
    except NameError:
        # handle future annotations.
        # functions might have dependecies in them
        # and we don't have the container context here so
        # we can't call _get_type_hints
        ret_annotation = unwrapped.__annotations__["return"]

        try:
            return_type = get_return_annotation(
                ret_annotation,
                context=get_fn_ns(unwrapped),
            )
        except NameError as e:
            msg = f"Factory {factory.__qualname__} does not specify return type. Or it's type is not defined yet."
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


@dataclasses.dataclass(slots=True, kw_only=True)
class InitializedProvider(Generic[_T]):
    provider: Provider[_T]
    type: type[_T]
    dependency_extractor: SupportsDependencyExtraction

    _dependencies: tuple[Dependency[object], ...] | None = None

    def dependencies(
        self, context: dict[str, Any]
    ) -> tuple[Dependency[object], ...]:
        if self._dependencies is None:
            self._dependencies = (
                self.dependency_extractor.extract_dependencies(
                    provider=self.provider, context=context
                )
            )
        return self._dependencies


def initialize_provider(
    provider: Provider[_T],
    extensions: Sequence[Extension],
) -> InitializedProvider[_T]:
    for extension in extensions:
        if not isinstance(
            extension, SupportsDependencyExtraction
        ) or not extension.extract_supports(provider):
            continue
        break
    else:
        msg = f"Couldn't find appropriate {SupportsDependencyExtraction.__name__} extension for provider {provider!r}"
        raise ValueError(msg)

    return InitializedProvider(
        provider=provider,
        dependency_extractor=extension,
        type=extension.extract_type(provider),
    )


class DependencyLifetime(enum.Enum):
    transient = enum.auto()
    scoped = enum.auto()
    singleton = enum.auto()


@runtime_checkable
class Provider(Protocol[_T]):
    impl: Any
    type_: type[_T]
    lifetime: DependencyLifetime
    is_async: bool
    is_generator: bool

    async def provide(self, kwargs: Mapping[str, Any]) -> _T: ...

    def provide_sync(self, kwargs: Mapping[str, Any]) -> _T: ...

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
        self.is_async = inspect.iscoroutinefunction(self.impl)
        self.is_generator = is_context_manager_function(self.impl)

    def provide_sync(self, kwargs: Mapping[str, Any]) -> _T:
        return self.impl(**kwargs)  # type: ignore[return-value]

    async def provide(self, kwargs: Mapping[str, Any]) -> _T:
        if self.is_async:
            return await self.impl(**kwargs)  # type: ignore[misc]

        return self.provide_sync(kwargs)


class Singleton(Scoped[_T]):
    lifetime = DependencyLifetime.singleton


class Transient(Scoped[_T]):
    lifetime = DependencyLifetime.transient


class Object(Provider[_T]):
    _type_hints: ClassVar[dict[str, Any]] = {}
    is_async = False
    is_generator = False
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
