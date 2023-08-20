from __future__ import annotations

import contextlib
import contextvars
import inspect
from collections.abc import Callable, Coroutine, Iterable
from contextlib import AsyncExitStack, ExitStack
from contextvars import ContextVar
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    TypeAlias,
    TypeVar,
    Union,
    overload,
)

from typing_extensions import Self

from aioinject.providers import Dependency
from aioinject.utils import await_maybe, enter_context_maybe


if TYPE_CHECKING:
    from aioinject.containers import Container

_T = TypeVar("_T")

_AnyCtx: TypeAlias = Union["InjectionContext", "SyncInjectionContext"]
_TypeAndImpl: TypeAlias = tuple[type[_T], _T | None]
_ExitStackT = TypeVar("_ExitStackT")

context_var: ContextVar[_AnyCtx] = ContextVar("aioinject_context")
container_var: ContextVar[Container] = ContextVar("aioinject_container")


class _BaseInjectionContext(Generic[_ExitStackT]):
    _token: contextvars.Token[_AnyCtx] | None
    _exit_stack_type: type[_ExitStackT]

    def __init__(self, container: Container) -> None:
        self._container = container
        self._exit_stack = self._exit_stack_type()
        self._cache: dict[_TypeAndImpl[Any], Any] = {}
        self._token = None

    def __class_getitem__(
        cls,
        item: type[_ExitStackT],
    ) -> _BaseInjectionContext[type[_ExitStackT]]:
        return type(  # type: ignore[return-value]
            f"_BaseInjectionContext[{item.__class__.__name__}]",
            (cls,),
            {"_exit_stack_type": item},
        )


class InjectionContext(_BaseInjectionContext[AsyncExitStack]):
    async def resolve(
        self,
        type_: type[_T],
        impl: Any | None = None,
        *,
        use_cache: bool = True,
    ) -> _T:
        if use_cache and (type_, impl) in self._cache:
            return self._cache[type_, impl]

        provider = self._container.get_provider(type_, impl)
        dependencies = {
            dep.name: await self.resolve(
                type_=dep.type_,
                impl=dep.implementation,
                use_cache=dep.use_cache,
            )
            for dep in provider.dependencies
        }

        resolved = enter_context_maybe(
            resolved=await provider.provide(**dependencies),
            stack=self._exit_stack,
        )
        resolved = await await_maybe(resolved)
        if use_cache:
            self._cache[type_, impl] = resolved
        return resolved

    @overload
    async def execute(
        self,
        function: Callable[..., Coroutine[Any, Any, _T]],
        dependencies: Iterable[Dependency[object]],
        *args: Any,
        **kwargs: Any,
    ) -> _T:
        ...

    @overload
    async def execute(
        self,
        function: Callable[..., _T],
        dependencies: Iterable[Dependency[object]],
        *args: Any,
        **kwargs: Any,
    ) -> _T:
        ...

    async def execute(
        self,
        function: Callable[..., Coroutine[Any, Any, _T] | _T],
        dependencies: Iterable[Dependency[object]],
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

    async def __aenter__(self) -> Self:
        self._token = context_var.set(self)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        context_var.reset(self._token)  # type: ignore[arg-type]
        await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)


class SyncInjectionContext(_BaseInjectionContext[ExitStack]):
    def resolve(
        self,
        type_: type[_T],
        impl: Any | None = None,
        *,
        use_cache: bool = True,
    ) -> _T:
        if use_cache and (type_, impl) in self._cache:
            return self._cache[type_, impl]

        provider = self._container.get_provider(type_, impl)
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
            resolved = self._exit_stack.enter_context(resolved)  # type: ignore[arg-type]
        if use_cache:
            self._cache[type_, impl] = resolved
        return resolved

    def execute(
        self,
        function: Callable[..., _T],
        dependencies: Iterable[Dependency[object]],
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

    def __enter__(self) -> Self:
        self._token = context_var.set(self)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        context_var.reset(self._token)  # type: ignore[arg-type]
        self._exit_stack.__exit__(exc_type, exc_val, exc_tb)
