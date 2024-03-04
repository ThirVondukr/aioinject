import contextlib
from collections.abc import Iterator, Sequence
from contextlib import AsyncExitStack
from types import TracebackType
from typing import Any, TypeAlias, TypeVar

from typing_extensions import Self

from aioinject._store import SingletonStore
from aioinject.context import InjectionContext, SyncInjectionContext
from aioinject.extensions import Extension, LifespanExtension
from aioinject.providers import Provider


_T = TypeVar("_T")
_Providers: TypeAlias = dict[type[_T], Provider[_T]]


class Container:
    def __init__(self, extensions: Sequence[Extension] | None = None) -> None:
        self._exit_stack = AsyncExitStack()
        self._singletons = SingletonStore(exit_stack=self._exit_stack)

        self.extensions = extensions or []
        self.providers: _Providers[Any] = {}
        self.type_context: dict[str, type[Any]] = {}

    def register(
        self,
        provider: Provider[Any],
    ) -> None:
        if provider.type_ in self.providers:
            msg = f"Provider for type {provider.type_} is already registered"
            raise ValueError(msg)

        self.providers[provider.type_] = provider
        if class_name := getattr(provider.type_, "__name__", None):
            self.type_context[class_name] = provider.type_

    def get_provider(self, type_: type[_T]) -> Provider[_T]:
        try:
            return self.providers[type_]
        except KeyError as exc:
            err_msg = f"Provider for type {type_.__qualname__} not found"
            raise ValueError(err_msg) from exc

    def context(self) -> InjectionContext:
        return InjectionContext(
            container=self,
            singletons=self._singletons,
        )

    def sync_context(self) -> SyncInjectionContext:
        return SyncInjectionContext(
            container=self,
            singletons=self._singletons,
        )

    @contextlib.contextmanager
    def override(self, *providers: Provider[Any]) -> Iterator[None]:
        previous: dict[type[Any], Provider[Any] | None] = {}
        for provider in providers:
            previous[provider.type_] = self.providers.get(provider.type_)
            self.providers[provider.type_] = provider

        yield

        for provider in providers:
            del self.providers[provider.type_]
            prev = previous[provider.type_]
            if prev is not None:
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
