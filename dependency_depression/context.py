from __future__ import annotations

import contextlib
from contextvars import ContextVar
from typing import TYPE_CHECKING, ContextManager, Optional, Type, TypeVar

if TYPE_CHECKING:
    from .containers import Depression

_T = TypeVar("_T")

context_var: ContextVar[DepressionContext] = ContextVar("depression_context")


class DepressionContext:
    def __init__(self, container: Depression):
        self.container = container
        self.cache: dict[Type[_T], _T] = {}
        self.exit_stack = contextlib.ExitStack()
        self._token = None

    def resolve_sync(
        self,
        interface: Type[_T],
        impl: Optional[Type] = None,
        use_cache: bool = True,
    ) -> _T:
        if use_cache and impl in self.cache:
            return self.cache[impl]

        provider = self.container.get_provider(interface, impl)
        dependencies = {
            dep.name: self.resolve_sync(
                interface=dep.interface,
                impl=dep.impl,
                use_cache=dep.use_cache,
            )
            for dep in provider.dependencies
        }
        resolved = provider.provide_sync(**dependencies)
        if isinstance(resolved, contextlib.ContextDecorator):
            resolved = self.exit_stack.enter_context(resolved)

        if use_cache:
            self.cache[impl] = resolved
        return resolved

    def __enter__(self):
        self._token = context_var.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        context_var.reset(self._token)
        self.exit_stack.close()
