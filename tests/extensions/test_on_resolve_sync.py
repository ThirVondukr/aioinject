import collections

import pytest

from aioinject import (
    Container,
    Object,
    Provider,
    Scoped,
    Singleton,
    SyncInjectionContext,
    Transient,
)
from aioinject._types import T
from aioinject.extensions import SyncOnResolveExtension


class _TestExtension(SyncOnResolveExtension):
    def __init__(self) -> None:
        self.type_counter: dict[type[object], int] = collections.defaultdict(
            int,
        )

    def on_resolve_sync(
        self,
        context: SyncInjectionContext,  # noqa: ARG002
        provider: Provider[T],
        instance: T,  # noqa: ARG002
    ) -> None:
        self.type_counter[provider.type_] += 1


@pytest.mark.parametrize(
    "provider",
    [
        Object(0),
        Scoped(int),
        Transient(int),
        Singleton(int),
    ],
)
def test_on_resolve(provider: Provider[int]) -> None:
    container = Container()
    container.register(provider)

    extension = _TestExtension()
    with container.sync_context(extensions=(extension,)) as ctx:
        for i in range(1, 10 + 1):
            number = ctx.resolve(int)
            assert number == 0
            assert extension.type_counter[int] == (
                i if isinstance(provider, Transient) else 1
            )
