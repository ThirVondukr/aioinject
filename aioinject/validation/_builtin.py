from collections.abc import Callable, Sequence
from typing import Any

import aioinject
from aioinject import Provider
from aioinject.validation.abc import ContainerValidator
from aioinject.validation.error import (
    ContainerValidationError,
    DependencyNotFoundError,
)


def all_dependencies_are_present(
    container: aioinject.Container,
) -> Sequence[ContainerValidationError]:
    errors = []
    for provider in container.providers.values():
        for dependency in provider.dependencies:
            if dependency.type_ not in container.providers:
                error = DependencyNotFoundError(
                    message=f"Provider for type {dependency.type_} not found",
                    dependency=dependency.type_,
                )
                errors.append(error)

    return errors


class ForbidDependency(ContainerValidator):
    def __init__(
        self,
        dependant: Callable[[Provider[Any]], bool],
        dependency: Callable[[Provider[Any]], bool],
    ) -> None:
        self.dependant = dependant
        self.dependency = dependency

    def __call__(
        self,
        container: aioinject.Container,
    ) -> Sequence[ContainerValidationError]:
        errors = []
        for provider in container.providers.values():
            if not self.dependant(provider):
                continue

            for dependency in provider.dependencies:
                dependency_provider = container.get_provider(
                    type_=dependency.type_,
                )
                if self.dependency(dependency_provider):
                    msg = f"Provider {provider!r} cannot depend on {dependency_provider!r}"
                    errors.append(ContainerValidationError(msg))
        return errors
