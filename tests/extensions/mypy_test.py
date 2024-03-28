from typing import Any

import aioinject
from aioinject import InjectionContext, Provider, SyncInjectionContext
from aioinject.extensions import OnResolveExtension, SyncOnResolveExtension


class _TestExtension(SyncOnResolveExtension, OnResolveExtension):

    async def on_resolve(
        self,
        context: InjectionContext,
        provider: Provider[Any],
        instance: Any,
    ) -> None: ...

    def on_resolve_sync(
        self,
        context: SyncInjectionContext,
        provider: Provider[Any],
        instance: Any,
    ) -> None: ...


async def _pass() -> None:
    # Same extension should be compatible with both contexts
    container = aioinject.Container()
    container.context(extensions=[_TestExtension()])
    container.sync_context(extensions=[_TestExtension()])
