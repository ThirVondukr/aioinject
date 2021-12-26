from __future__ import annotations

import abc
import asyncio
import collections.abc
import functools
import inspect
import threading
import typing
import typing as t
from inspect import isclass
from typing import Any, Iterable, NamedTuple, Optional, Sequence, Type, Union

from dependency_depression.markers import Impl, Inject, NoCache

_T = t.TypeVar("_T")


class _Dependency(NamedTuple):
    name: str
    interface: Type[_T]
    impl: Any
    use_cache: bool


def collect_dependencies(type_hints: dict[str, any]) -> Iterable[_Dependency]:
    for name, hint in type_hints.items():
        try:
            dep_type, *args = typing.get_args(hint)
        except ValueError:
            dep_type, args = hint, tuple()
        dep_impl = next((impl.type for impl in args if isinstance(impl, Impl)), None)

        if Inject not in args:
            continue

        yield _Dependency(
            name=name,
            interface=dep_type,
            impl=dep_impl,
            use_cache=NoCache not in args,
        )


def _get_hints(provider: Provider):
    source = provider.factory
    if inspect.isclass(source):
        source = source.__init__

    type_hints = typing.get_type_hints(source, include_extras=True)
    return type_hints


_ITERABLES = {
    collections.abc.Generator,
    collections.abc.AsyncGenerator,
    collections.abc.Iterable,
    collections.abc.AsyncIterable,
}


def _guess_impl(factory) -> type:
    if isclass(factory):
        return factory
    type_hints = typing.get_type_hints(factory)
    try:
        return_type = type_hints["return"]
    except KeyError as e:
        raise ValueError(
            f"factory {factory.__qualname__} does not specify return type."
        ) from e

    if origin := typing.get_origin(return_type):
        args = typing.get_args(return_type)
        if origin in _ITERABLES:
            return args[0]
    return return_type


class Provider(t.Generic[_T], abc.ABC):
    def __init__(
        self,
        impl: type,
    ):
        self.impl = impl

    @abc.abstractmethod
    def provide_sync(self, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    async def provide(self, **kwargs):
        raise NotImplementedError

    @property
    def type_hints(self):
        raise NotImplementedError

    @property
    def is_async(self) -> bool:
        raise NotImplementedError

    @functools.cached_property
    def dependencies(self) -> Sequence[_Dependency]:
        return tuple(collect_dependencies(self.type_hints))


class Callable(Provider):
    def __init__(
        self,
        factory: Union[t.Callable[..., _T], Type[_T]],
        impl: Optional[Type[_T]] = None,
    ):
        super().__init__(
            impl=impl or _guess_impl(factory),
        )
        self.factory = factory

    def provide_sync(self, **kwargs):
        return self.factory(**kwargs)

    async def provide(self, **kwargs):
        if self.is_async:
            return await self.factory(**kwargs)
        return self.provide_sync()

    @functools.cached_property
    def type_hints(self):
        type_hints = _get_hints(self)
        if "return" in type_hints:
            del type_hints["return"]
        return type_hints

    @functools.cached_property
    def is_async(self) -> bool:
        return inspect.iscoroutinefunction(self.factory)


class Singleton(Callable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache: Optional[_T] = None
        self._lock = threading.Lock()
        self._async_lock = asyncio.Lock()

    def provide_sync(self, **kwargs) -> _T:
        if self.cache is None:
            with self._lock:
                if self.cache is None:
                    self.cache = super().provide_sync(**kwargs)
        return self.cache

    async def provide(self, **kwargs) -> _T:
        if self.cache is None:
            async with self._async_lock:
                if self.cache is None:
                    self.cache = await super(Singleton, self).provide()
        return self.cache


class Object(Provider):
    is_async = False
    type_hints = {}

    def __init__(
        self,
        object_: _T,
        impl: Optional[type] = None,
    ):
        super().__init__(
            impl=impl or type(object_),
        )
        self.object = object_

    def provide_sync(self, **kwargs):
        return self.object

    async def provide(self, **kwargs):
        return self.object
