from collections.abc import Sequence

from aioinject import Scoped, Singleton
from aioinject.validation._builtin import (
    ForbidDependency,
    all_dependencies_are_present,
)
from aioinject.validation._validate import validate_container
from aioinject.validation.abc import ContainerValidator


forbid_singleton_on_scoped_dependency = ForbidDependency(
    dependant=lambda p: isinstance(p.provider, Singleton),
    dependency=lambda p: isinstance(p.provider, Scoped)
    and not isinstance(p.provider, Singleton),
)

DEFAULT_VALIDATORS: Sequence[ContainerValidator] = [
    all_dependencies_are_present,
    forbid_singleton_on_scoped_dependency,
]

__all__ = [
    "DEFAULT_VALIDATORS",
    "ContainerValidator",
    "all_dependencies_are_present",
    "ForbidDependency",
    "validate_container",
]
