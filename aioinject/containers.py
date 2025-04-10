import contextlib
from collections import defaultdict
from collections.abc import Iterator, Mapping, Sequence
from contextlib import AsyncExitStack
from types import TracebackType
from typing import Any

from typing_extensions import Self

from aioinject import _types
from aioinject._features.generics import get_generic_origin
from aioinject._store import SingletonStore
from aioinject._types import T
from aioinject.context import InjectionContext, SyncInjectionContext
from aioinject.extensions import (
    ContextExtension,
    Extension,
    LifespanExtension,
    OnInitExtension,
    SyncContextExtension,
)
from aioinject.providers import Provider


class Container:
    def __init__(self, extensions: Sequence[Extension] | None = None) -> None:
        self._exit_stack = AsyncExitStack()
        self._singletons = SingletonStore(exit_stack=self._exit_stack)

        self.providers: _types.Providers[Any] = defaultdict(list)
        self.type_context: dict[str, type[Any]] = {}
        self.extensions = extensions or []
        self._init_extensions(self.extensions)

    def _init_extensions(self, extensions: Sequence[Extension]) -> None:
        for extension in extensions:
            if isinstance(extension, OnInitExtension):
                extension.on_init(self)

    def register(self, *providers: Provider[Any]) -> None:
        for provider in providers:
            self._register(provider)

    def try_register(self, *providers: Provider[Any]) -> None:
        for provider in providers:
            with contextlib.suppress(ValueError):
                self._register(provider)

    def _register(self, provider: Provider[Any]) -> None:
        if any(
            provider.impl == existing_provider.impl
            for existing_provider in self.providers.get(provider.type_, [])
        ):
            msg = (
                f"Provider for type {provider.type_} with same "
                f"implementation already registered"
            )
            raise ValueError(msg)

        self.providers[provider.type_].append(provider)

        class_name = getattr(provider.type_, "__name__", None)
        if class_name and class_name not in self.type_context:
            self.type_context[class_name] = get_generic_origin(provider.type_)

    def get_provider(self, type_: type[T]) -> Provider[T]:
        return self.get_providers(type_)[0]

    def get_providers(self, type_: type[T]) -> list[Provider[T]]:
        if providers := self.providers[type_]:
            return providers

        err_msg = f"Providers for type {type_.__qualname__} not found"
        raise ValueError(err_msg)

    def context(
        self,
        context: Mapping[Any, Any] | None = None,
        extensions: Sequence[ContextExtension] = (),
    ) -> InjectionContext:
        return InjectionContext(
            container=self,
            singletons=self._singletons,
            extensions=extensions,
            context=context,
        )

    def sync_context(
        self,
        context: Mapping[Any, Any] | None = None,
        extensions: Sequence[SyncContextExtension] = (),
    ) -> SyncInjectionContext:
        return SyncInjectionContext(
            container=self,
            singletons=self._singletons,
            extensions=extensions,
            context=context,
        )

    @contextlib.contextmanager
    def override(self, *providers: Provider[Any]) -> Iterator[None]:
        previous = {
            provider.type_: self.providers.get(provider.type_, None)
            for provider in providers
        }
        overridden = defaultdict(
            list,
            {provider.type_: [provider] for provider in providers},
        )

        self.providers.update(overridden)

        try:
            yield
        finally:
            for provider in providers:
                del self.providers[provider.type_]
                if (prev := previous[provider.type_]) is not None:
                    self.providers[provider.type_] = prev

    async def __aenter__(self) -> Self:
        for extension in self.extensions:
            if isinstance(extension, LifespanExtension):
                await self._exit_stack.enter_async_context(
                    extension.lifespan(self),
                )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self._singletons.__aexit__(exc_type, exc_val, exc_tb)

    async def aclose(self) -> None:
        await self.__aexit__(None, None, None)  # pragma: no cover

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._singletons.__exit__(exc_type, exc_val, exc_tb)

    def close(self) -> None:
        self.__exit__(None, None, None)  # pragma: no cover
