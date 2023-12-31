from collections.abc import Sequence
from typing import Protocol

import aioinject
from aioinject.validation.error import ContainerValidationError


class ContainerValidator(Protocol):
    def __call__(
        self,
        container: aioinject.Container,
    ) -> Sequence[ContainerValidationError]:
        ...
