import dataclasses
from collections.abc import Sequence
from typing import Any


@dataclasses.dataclass(slots=True, frozen=True)
class ContainerValidationError:
    message: str


@dataclasses.dataclass(slots=True, frozen=True)
class DependencyNotFoundError(ContainerValidationError):
    dependency: type[Any]


@dataclasses.dataclass
class ContainerValidationErrorGroup(Exception):  # noqa: N818
    # Exception group could be used instead, but it's added in python 3.11
    errors: Sequence[ContainerValidationError]

    def __str__(self) -> str:
        return repr(self)  # pragma: no cover
