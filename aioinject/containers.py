import contextlib
from collections.abc import Iterator
from types import TracebackType
from typing import Any, TypeAlias, TypeVar

from typing_extensions import Self

from aioinject._store import SingletonStore
from aioinject.context import InjectionContext, SyncInjectionContext
from aioinject.providers import Provider


_T = TypeVar("_T")
_Providers: TypeAlias = dict[type[_T], Provider[_T]]


class Container:
    def __init__(self) -> None:
        self.providers: _Providers[Any] = {}
        self._singletons = SingletonStore()
        self._unresolved_providers: list[Provider[Any]] = []
        self._type_context: dict[str, type[Any]] = {}

    def _resolve_unresolved_provider(self) -> None:
        for provider in self._unresolved_providers:
            with contextlib.suppress(NameError):
                self._register_impl(provider)
                self._unresolved_providers.remove(provider)


    def _register_impl(self, provider: Provider[Any]) -> None:
            provider_type = provider.resolve_type(self._type_context)
            if provider_type in self.providers:
                msg = f"Provider for type {provider_type} is already registered"
                raise ValueError(msg)
            self.providers[provider_type] = provider
            if klass_name := getattr(provider_type, "__name__" , None):
                self._type_context[klass_name] = provider_type


    def register(
        self,
        provider: Provider[Any],
    ) -> None:  
        try:
            self._register_impl(provider)
        except NameError:
            self._unresolved_providers.append(provider)
        self._resolve_unresolved_provider()


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
    def override(
        self,
        provider: Provider[Any],
    ) -> Iterator[None]:
        previous = self.providers.get(provider.type_)
        self.providers[provider.type_] = provider

        yield

        del self.providers[provider.type_]
        if previous is not None:
            self.providers[provider.type_] = previous

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self._singletons.__aexit__(exc_type, exc_val, exc_tb)

    async def aclose(self) -> None:
        await self.__aexit__(None, None, None)
