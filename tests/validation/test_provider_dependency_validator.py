from collections.abc import Sequence
from typing import Any

import pytest

from aioinject import Callable, Container, Provider, Singleton
from aioinject.validation import ForbidDependency, validate_container
from aioinject.validation.error import (
    ContainerValidationErrorGroup,
)


_VALIDATORS = [
    ForbidDependency(
        dependant=lambda p: isinstance(p, Singleton),
        dependency=lambda p: isinstance(p, Callable) and not isinstance(p, Singleton),
    ),
]


def _str_dependency(number: int) -> str:
    return str(number)


@pytest.mark.parametrize(
    "providers",
    [
        [Callable(int)],
        [Callable(_str_dependency), Callable(int)],
        [Callable(_str_dependency), Singleton(int)],
        [Singleton(_str_dependency), Singleton(int)],
    ],
)
def test_ok(providers: Sequence[Provider[Any]]) -> None:
    container = Container()
    for provider in providers:
        container.register(provider)

    validate_container(container, _VALIDATORS)


@pytest.mark.parametrize(
    "providers",
    [
        [Singleton(_str_dependency), Callable(int)],
    ],
)
def test_err(providers: Sequence[Provider[Any]]) -> None:
    container = Container()
    for provider in providers:
        container.register(provider)

    with pytest.raises(ContainerValidationErrorGroup):
        validate_container(container, _VALIDATORS)
