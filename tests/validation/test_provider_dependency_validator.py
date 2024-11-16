from collections.abc import Sequence
from typing import Any

import pytest

from aioinject import Container, Provider, Scoped, Singleton
from aioinject.validation import (
    forbid_singleton_on_scoped_dependency,
    validate_container,
)
from aioinject.validation.error import (
    ContainerValidationErrorGroup,
)


_VALIDATORS = [
    forbid_singleton_on_scoped_dependency,
]


def _str_dependency(number: int) -> str:
    return str(number)


@pytest.mark.parametrize(
    "providers",
    [
        [Scoped(int)],
        [Scoped(_str_dependency), Scoped(int)],
        [Scoped(_str_dependency), Singleton(int)],
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
        [Singleton(_str_dependency), Scoped(int)],
    ],
)
def test_err(providers: Sequence[Provider[Any]]) -> None:
    container = Container()
    for provider in providers:
        container.register(provider)

    with pytest.raises(ContainerValidationErrorGroup):
        validate_container(container, _VALIDATORS)
