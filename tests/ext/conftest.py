import pytest

import aioinject


@pytest.fixture(scope="session")
def provided_value() -> int:
    return 42


class NumberService:
    async def get_number(self, number: int) -> int:
        return number


@pytest.fixture(scope="session")
def container(provided_value: int) -> aioinject.Container:
    container = aioinject.Container()
    container.register(aioinject.Object(provided_value))
    container.register(aioinject.Callable(NumberService))
    return container
