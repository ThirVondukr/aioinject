import pytest

from aioinject import Container, providers
from aioinject.validation import (
    all_providers_for_type_have_equal_lifetime,
    validate_container,
)
from aioinject.validation.error import ContainerValidationErrorGroup


_VALIDATORS = [all_providers_for_type_have_equal_lifetime]


class IDependency:
    pass


class SingletonImpl(IDependency):
    pass


class ScopedImpl(IDependency):
    pass


def test_ok() -> None:
    container = Container()
    container.register(providers.Scoped(ScopedImpl, type_=IDependency))
    container.register(providers.Scoped(SingletonImpl, type_=IDependency))

    validate_container(container, _VALIDATORS)


def test_err() -> None:
    container = Container()
    container.register(providers.Scoped(ScopedImpl, type_=IDependency))
    container.register(providers.Singleton(SingletonImpl, type_=IDependency))

    with pytest.raises(ContainerValidationErrorGroup) as exc_info:
        validate_container(container, _VALIDATORS)

    assert len(exc_info.value.errors) == 1
    err = exc_info.value.errors[0]
    assert "has providers with different scopes" in err.message
