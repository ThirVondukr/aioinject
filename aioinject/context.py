from __future__ import annotations

import contextlib
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, Optional, Type, TypeVar, Union

if TYPE_CHECKING:
    from .containers import Container

_T = TypeVar("_T")

_AnyCtx = Union["InjectionContext", "SyncInjectionContext"]
context_var: ContextVar[_AnyCtx] = ContextVar("aioinject_context")


class _BaseInjectionContext:
    def __init__(self, container: Container):
        self.container = container
        self.cache: dict[tuple[Type[_T], Optional[Any]], _T] = {}
        self._token = None


class InjectionContext(_BaseInjectionContext):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.exit_stack = contextlib.AsyncExitStack()

    async def resolve(
        self,
        type_: Type[_T],
        impl: Optional[Type] = None,
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
            resolved = self.exit_stack.enter_context(resolved)

        if isinstance(resolved, contextlib.AsyncContextDecorator):
            resolved = await self.exit_stack.enter_async_context(resolved)

        if use_cache:
            self.cache[type_, impl] = resolved
        return resolved

    async def __aenter__(self) -> InjectionContext:
        self._token = context_var.set(self)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        context_var.reset(self._token)
        await self.exit_stack.__aexit__(exc_type, exc_val, exc_tb)


class SyncInjectionContext(_BaseInjectionContext):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.exit_stack = contextlib.ExitStack()

    def resolve(
        self,
        interface: Type[_T],
        impl: Optional[Any] = None,
        use_cache: bool = True,
    ) -> _T:
        if use_cache and (interface, impl) in self.cache:
            return self.cache[interface, impl]

        provider = self.container.get_provider(interface, impl)
        dependencies = {
            dep.name: self.resolve(
                interface=dep.type,
                impl=dep.implementation,
                use_cache=dep.use_cache,
            )
            for dep in provider.dependencies
        }

        resolved = provider.provide_sync(**dependencies)
        if isinstance(resolved, contextlib.ContextDecorator):
            resolved = self.exit_stack.enter_context(resolved)

        if use_cache:
            self.cache[interface, impl] = resolved
        return resolved

    def __enter__(self) -> SyncInjectionContext:
        self._token = context_var.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        context_var.reset(self._token)
        self.exit_stack.__exit__(exc_type, exc_val, exc_tb)
