from __future__ import annotations

import contextlib
import contextvars
import inspect
import typing
from collections.abc import Callable, Coroutine, Iterable
from contextlib import AsyncExitStack, ExitStack
from contextvars import ContextVar
from types import TracebackType
from typing import TYPE_CHECKING, Any, Generic, Protocol, TypeVar, Union

from .providers import Dependency, Provider, Singleton

if TYPE_CHECKING:
    from .containers import Container

_T = TypeVar("_T")

_AnyCtx = Union["InjectionContext", "SyncInjectionContext"]
context_var: ContextVar[_AnyCtx] = ContextVar("aioinject_context")

container_var: ContextVar[Container] = ContextVar("aioinject_container")

TypeAndImpl = tuple[type[_T], _T | None]
TExitStack = TypeVar("TExitStack")


class DICache(Protocol):
    def __setitem__(self, key: TypeAndImpl[_T], value: _T) -> None:
        ...  # pragma: no cover

    def __getitem__(self, item: TypeAndImpl[_T]) -> _T:
        ...  # pragma: no cover

    def __contains__(self, item: TypeAndImpl) -> bool:
        ...  # pragma: no cover


class _BaseInjectionContext(Generic[TExitStack]):
    _token: contextvars.Token | None
    _exit_stack_type: type[TExitStack]

    def __init__(
        self,
        container: Container,
        singleton_exit_stack: AsyncExitStack,
    ) -> None:
        self.container = container
        self.singleton_exit_stack = singleton_exit_stack
        self.exit_stack = self._exit_stack_type()
        self.cache: DICache = {}
        self._token = None

    def __class_getitem__(
        cls,
        item: type[TExitStack],
    ) -> _BaseInjectionContext[TExitStack]:
        return type(  # type: ignore[return-value]
            f"_BaseInjectionContext[{item.__class__.__name__}]",
            (cls,),
            {"_exit_stack_type": item},
        )

    def _get_exit_stack(
        self,
        provider: Provider,
    ) -> TExitStack | AsyncExitStack:
        if isinstance(provider, Singleton):
            return self.singleton_exit_stack
        return self.exit_stack

    def _update_singleton_cache(
        self,
        provider: Provider,
        resolved_value: Any,
    ) -> None:
        if not isinstance(provider, Singleton):
            return
        provider.cache = resolved_value


class InjectionContext(_BaseInjectionContext[AsyncExitStack]):
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
                type_=dep.type_,
                impl=dep.implementation,
                use_cache=dep.use_cache,
            )
            for dep in provider.dependencies
        }

        resolved = await provider.provide(**dependencies)
        stack = self._get_exit_stack(provider=provider)

        if isinstance(resolved, contextlib.ContextDecorator):
            resolved = stack.enter_context(resolved)  # type: ignore[arg-type]

        if isinstance(resolved, contextlib.AsyncContextDecorator):
            resolved = await stack.enter_async_context(
                resolved,  # type: ignore[arg-type]
            )
        self._update_singleton_cache(
            provider=provider,
            resolved_value=resolved,
        )
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
        ...  # pragma: no cover

    @typing.overload
    async def execute(
        self,
        function: Callable[..., _T],
        dependencies: Iterable[Dependency],
        *args: Any,
        **kwargs: Any,
    ) -> _T:
        ...  # pragma: no cover

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
                type_=dependency.type_,
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


class SyncInjectionContext(_BaseInjectionContext[ExitStack]):
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
                type_=dep.type_,
                impl=dep.implementation,
                use_cache=dep.use_cache,
            )
            for dep in provider.dependencies
        }

        resolved = provider.provide_sync(**dependencies)
        if isinstance(resolved, contextlib.ContextDecorator):
            resolved = self.exit_stack.enter_context(resolved)  # type: ignore[arg-type]
        self._update_singleton_cache(
            provider=provider,
            resolved_value=resolved,
        )
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
                type_=dependency.type_,
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
