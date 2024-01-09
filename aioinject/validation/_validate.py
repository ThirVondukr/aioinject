from collections.abc import Iterable

import aioinject
from aioinject.validation.abc import ContainerValidator
from aioinject.validation.error import (
    ContainerValidationError,
    ContainerValidationErrorGroup,
)


def validate_container(
    container: aioinject.Container,
    validators: Iterable[ContainerValidator],
) -> None:
    errors: list[ContainerValidationError] = []
    for validator in validators:
        errors.extend(validator.__call__(container))

    if errors:
        raise ContainerValidationErrorGroup(errors=errors)
