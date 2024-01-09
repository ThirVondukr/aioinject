from collections.abc import Iterable

import aioinject
from aioinject.validation.abc import ContainerValidator
from aioinject.validation.error import (
    ContainerValidationErrorGroup,
)


def validate_container(
    container: aioinject.Container,
    validators: Iterable[ContainerValidator],
) -> None:
    for validator in validators:
        errors = validator(container)

        if errors:
            raise ContainerValidationErrorGroup(errors=errors)
