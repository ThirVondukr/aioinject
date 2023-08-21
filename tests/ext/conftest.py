import pytest

import aioinject


@pytest.fixture(scope="session")
def provided_value() -> int:
    return 42


@pytest.fixture(scope="session")
def container(provided_value: int) -> aioinject.Container:
    container = aioinject.Container()
    container.register(aioinject.Object(provided_value))
    return container
