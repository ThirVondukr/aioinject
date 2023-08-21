from __future__ import annotations

import asyncio
import collections.abc
import functools
import inspect
import threading
import typing
from contextlib import AsyncExitStack
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
)

from aioinject.markers import Inject
from aioinject.utils import await_maybe, enter_context_maybe, remove_annotation


_T = TypeVar("_T")


@dataclass(slots=True)
class Dependency(Generic[_T]):
    name: str
    type_: type[_T]
    implementation: Any
    use_cache: bool


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
) -> typing.Iterable[Dependency[object]]:
    if not isinstance(dependant, dict):
        with remove_annotation(dependant.__annotations__, "return"):
            type_hints = typing.get_type_hints(dependant, include_extras=True)
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
            implementation=inject_marker.impl,
            use_cache=inject_marker.cache,
        )


def _get_provider_type_hints(provider: Provider[Any]) -> dict[str, Any]:
    source = provider.impl
    if inspect.isclass(source):
        source = source.__init__

    if isinstance(source, functools.partial):
        return {}

    type_hints = typing.get_type_hints(source, include_extras=True)
    for key, value in type_hints.items():
        _, args = _get_annotation_args(value)
        for arg in args:
            if isinstance(arg, Inject):
                break
        else:
            type_hints[key] = Annotated[value, Inject]

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


def _guess_impl(factory: _FactoryType[_T]) -> type[_T]:
    if isclass(factory):
        return typing.cast(type[_T], factory)
    type_hints = typing.get_type_hints(factory)
    try:
        return_type = type_hints["return"]
    except KeyError as e:
        err_msg = (
            f"factory {factory.__qualname__} does not specify return type."
        )
        raise ValueError(err_msg) from e

    if origin := typing.get_origin(return_type):
        args = typing.get_args(return_type)

        maybe_wrapped = getattr(  # @functools.wraps
            factory,
            "__wrapped__",
            factory,
        )
        if origin in _ASYNC_GENERATORS and inspect.isasyncgenfunction(
            maybe_wrapped,
        ):
            return args[0]
        if origin in _GENERATORS and inspect.isgeneratorfunction(
            maybe_wrapped,
        ):
            return args[0]
    return return_type


class Provider(Protocol[_T]):
    type: type[_T]  # noqa: A003
    impl: Any

    def __init__(
        self,
        type_: typing.Type[_T],  # noqa: UP006
        impl: Any,
    ) -> None:
        self.type = type_
        self.impl = impl

    def provide_sync(self, **kwargs: Any) -> _T:
        ...

    async def provide(self, **kwargs: Any) -> _T:
        ...

    @property
    def type_hints(self) -> dict[str, Any]:
        ...

    @property
    def is_async(self) -> bool:
        ...

    @functools.cached_property
    def dependencies(self) -> tuple[Dependency[object], ...]:
        return tuple(collect_dependencies(self.type_hints))


class Callable(Provider[_T]):
    def __init__(
        self,
        factory: _FactoryType[_T],
        type_: type[_T] | None = None,
    ) -> None:
        super().__init__(
            type_=type_ or _guess_impl(factory),
            impl=factory,
        )

    def provide_sync(self, **kwargs: Any) -> _T:
        return self.impl(**kwargs)

    async def provide(self, **kwargs: Any) -> _T:
        if self.is_async:
            return await self.impl(**kwargs)
        return self.provide_sync(**kwargs)

    @functools.cached_property
    def type_hints(self) -> dict[str, Any]:
        type_hints = _get_provider_type_hints(self)
        if "return" in type_hints:
            del type_hints["return"]
        return type_hints

    @functools.cached_property
    def is_async(self) -> bool:
        return inspect.iscoroutinefunction(self.impl)


Factory = Callable


class Singleton(Callable[_T]):
    def __init__(
        self,
        factory: _FactoryType[_T],
        type_: type[_T] | None = None,
    ) -> None:
        super().__init__(factory=factory, type_=type_)
        self.cache: _T | None = None
        self._lock = threading.Lock()
        self._async_lock = asyncio.Lock()
        self._exit_stack = AsyncExitStack()

    def provide_sync(self, **kwargs: Any) -> _T:
        if self.cache is None:
            with self._lock:
                if self.cache is None:
                    self.cache = super().provide_sync(**kwargs)
        return self.cache

    async def provide(self, **kwargs: Any) -> _T:
        if self.cache is None:
            async with self._async_lock:
                if self.cache is None:
                    awaitable = enter_context_maybe(
                        await super().provide(**kwargs),
                        self._exit_stack,
                    )
                    self.cache = await await_maybe(awaitable)
        return self.cache

    async def aclose(self) -> None:
        await self._exit_stack.aclose()


class Object(Provider[_T]):
    type_hints: ClassVar[dict[str, Any]] = {}
    is_async = False
    impl: _T

    def __init__(
        self,
        object_: _T,
        type_: type[_T] | None = None,
    ) -> None:
        super().__init__(
            type_=type_ or type(object_),
            impl=object_,
        )

    def provide_sync(self, **kwargs: Any) -> _T:  # noqa: ARG002
        return self.impl

    async def provide(self, **kwargs: Any) -> _T:  # noqa: ARG002
        return self.impl
