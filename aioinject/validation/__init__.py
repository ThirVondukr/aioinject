from collections.abc import Sequence

from aioinject import Scoped, Singleton
from aioinject.validation._builtin import (
    ForbidDependency,
    all_dependencies_are_present,
)
from aioinject.validation._validate import validate_container
from aioinject.validation.abc import ContainerValidator


DEFAULT_VALIDATORS: Sequence[ContainerValidator] = [
    all_dependencies_are_present,
    ForbidDependency(
        dependant=lambda p: isinstance(p, Singleton),
        dependency=lambda p: isinstance(p, Scoped)
        and not isinstance(p, Singleton),
    ),
]

__all__ = [
    "DEFAULT_VALIDATORS",
    "ContainerValidator",
    "all_dependencies_are_present",
    "ForbidDependency",
    "validate_container",
]
