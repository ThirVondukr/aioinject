from aioinject.containers import Container
from aioinject.context import InjectionContext, SyncInjectionContext
from aioinject.decorators import inject
from aioinject.markers import Inject, Injected
from aioinject.providers import (
    Object,
    Provider,
    Scoped,
    Singleton,
    Transient,
)


__all__ = [
    "Container",
    "Inject",
    "InjectionContext",
    "Object",
    "Provider",
    "Scoped",
    "Singleton",
    "SyncInjectionContext",
    "Transient",
    "inject",
    "Injected",
]

__version__ = "0.37.4"
