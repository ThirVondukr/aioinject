from collections.abc import Sequence
from typing import Any

import pytest

from aioinject import Callable, Container, Provider
from aioinject.validation import (
    all_dependencies_are_present,
    validate_container,
)
from aioinject.validation.error import (
    ContainerValidationErrorGroup,
    DependencyNotFoundError,
)


_VALIDATORS = [all_dependencies_are_present]


def _str_dependency(number: int) -> str:
    return str(number)


@pytest.mark.parametrize(
    "providers",
    [
        [Callable(int)],
        [Callable(_str_dependency), Callable(int)],
    ],
)
def test_ok(providers: Sequence[Provider[Any]]) -> None:
    container = Container()
    for provider in providers:
        container.register(provider)

    validate_container(container, _VALIDATORS)


def test_err() -> None:
    container = Container()
    container.register(Callable(_str_dependency))

    with pytest.raises(ContainerValidationErrorGroup) as exc_info:
        validate_container(container, _VALIDATORS)

    assert len(exc_info.value.errors) == 1
    err = exc_info.value.errors[0]
    assert isinstance(err, DependencyNotFoundError)
    assert err.dependency == int
