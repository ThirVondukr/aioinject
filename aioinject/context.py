from __future__ import annotations

import contextlib
import contextvars
import inspect
import typing
from collections.abc import Callable, Coroutine, Iterable
from contextvars import ContextVar
from types import TracebackType
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, Union

from .providers import Dependency

if TYPE_CHECKING:
    from .containers import Container

_T = TypeVar("_T")

_AnyCtx = Union["InjectionContext", "SyncInjectionContext"]
context_var: ContextVar[_AnyCtx] = ContextVar("aioinject_context")

container_var: ContextVar[Container] = ContextVar("aioinject_container")


TypeAndImpl = tuple[type[_T], _T | None]


class DiCache(Protocol):
    def __setitem__(self, key: TypeAndImpl[_T], value: _T) -> None:
        ...

    def __getitem__(self, item: TypeAndImpl[_T]) -> _T:
        ...

    def __contains__(self, item: TypeAndImpl) -> bool:
        ...


class _BaseInjectionContext:
    _token: contextvars.Token | None

    def __init__(self, container: Container) -> None:
        self.container = container
        self.cache: DiCache = {}
        self._token = None


class InjectionContext(_BaseInjectionContext):
    def __init__(self, container: Container) -> None:
        super().__init__(container=container)
        self.exit_stack = contextlib.AsyncExitStack()

    async def resolve(
        self,
        type_: type[_T],
        impl: Any | None = None,
        *,
        use_cache: bool = True,
    ) -> _T:
        if use_cache and (type_, impl) in self.cache:
            return self.cache[type_, impl]
        provider = self.container.get_provider(type_, impl)
        dependencies = {
            dep.name: await self.resolve(
                type_=dep.type,
                impl=dep.implementation,
                use_cache=dep.use_cache,
            )
            for dep in provider.dependencies
        }

        resolved = await provider.provide(**dependencies)
        if isinstance(resolved, contextlib.ContextDecorator):
            resolved = self.exit_stack.enter_context(resolved)  # type: ignore[arg-type]

        if isinstance(resolved, contextlib.AsyncContextDecorator):
            resolved = await self.exit_stack.enter_async_context(resolved)  # type: ignore[arg-type]

        if use_cache:
            self.cache[type_, impl] = resolved
        return resolved

    @typing.overload
    async def execute(
        self,
        function: Callable[..., Coroutine[Any, Any, _T]],
        dependencies: Iterable[Dependency],
        *args: Any,
        **kwargs: Any,
    ) -> _T:
        ...

    @typing.overload
    async def execute(
        self,
        function: Callable[..., _T],
        dependencies: Iterable[Dependency],
        *args: Any,
        **kwargs: Any,
    ) -> _T:
        ...

    async def execute(
        self,
        function: Callable[..., Coroutine[Any, Any, _T] | _T],
        dependencies: Iterable[Dependency],
        *args: Any,
        **kwargs: Any,
    ) -> _T:
        resolved = {}
        for dependency in dependencies:
            if dependency.name in kwargs:
                continue
            resolved[dependency.name] = await self.resolve(
                type_=dependency.type,
                impl=dependency.implementation,
                use_cache=dependency.use_cache,
            )
        if inspect.iscoroutinefunction(function):
            return await function(*args, **kwargs, **resolved)
        return function(*args, **kwargs, **resolved)  # type: ignore[return-value]

    async def __aenter__(self) -> InjectionContext:
        self._token = context_var.set(self)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        context_var.reset(self._token)  # type: ignore[arg-type]
        await self.exit_stack.__aexit__(exc_type, exc_val, exc_tb)


class SyncInjectionContext(_BaseInjectionContext):
    def __init__(self, container: Container) -> None:
        super().__init__(container=container)
        self.exit_stack = contextlib.ExitStack()

    def resolve(
        self,
        type_: type[_T],
        impl: Any | None = None,
        *,
        use_cache: bool = True,
    ) -> _T:
        if use_cache and (type_, impl) in self.cache:
            return self.cache[type_, impl]

        provider = self.container.get_provider(type_, impl)
        dependencies = {
            dep.name: self.resolve(
                type_=dep.type,
                impl=dep.implementation,
                use_cache=dep.use_cache,
            )
            for dep in provider.dependencies
        }

        resolved = provider.provide_sync(**dependencies)
        if isinstance(resolved, contextlib.ContextDecorator):
            resolved = self.exit_stack.enter_context(resolved)  # type: ignore[arg-type]

        if use_cache:
            self.cache[type_, impl] = resolved
        return resolved

    def execute(
        self,
        function: Callable[..., _T],
        dependencies: Iterable[Dependency],
        *args: Any,
        **kwargs: Any,
    ) -> _T:
        resolved = {}
        for dependency in dependencies:
            if dependency.name in kwargs:
                continue
            resolved[dependency.name] = self.resolve(
                type_=dependency.type,
                impl=dependency.implementation,
                use_cache=dependency.use_cache,
            )
        return function(*args, **kwargs, **resolved)

    def __enter__(self) -> SyncInjectionContext:
        self._token = context_var.set(self)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        context_var.reset(self._token)  # type: ignore[arg-type]
        self.exit_stack.__exit__(exc_type, exc_val, exc_tb)
