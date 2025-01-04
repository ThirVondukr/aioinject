from collections.abc import Callable, Sequence
from itertools import chain
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
    return [
        DependencyNotFoundError(
            message=f"Provider for type {dependency.type_} not found",
            dependency=dependency.type_,
        )
        for provider in chain.from_iterable(container.providers.values())
        for dependency in provider.collect_dependencies(container.type_context)
        if dependency.type_ not in container.providers
    ]


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
        for provider in chain.from_iterable(container.providers.values()):
            if not self.dependant(provider):
                continue

            for dependency in provider.collect_dependencies(
                container.type_context,
            ):
                dep_type = dependency.type_
                dependency_provider = container.get_provider(
                    type_=dep_type,
                )
                if self.dependency(dependency_provider):
                    msg = f"Provider {provider!r} cannot depend on {dependency_provider!r}"
                    errors.append(ContainerValidationError(msg))

        return errors


def all_providers_for_type_have_equal_lifetime(
    container: aioinject.Container,
) -> Sequence[ContainerValidationError]:
    return [
        ContainerValidationError(
            f"Type {type_} has providers with different scopes"
        )
        for type_, providers in container.providers.items()
        if len({provider.lifetime for provider in providers}) > 1
    ]
