import uuid
from typing import TypedDict

import pytest

import aioinject


@pytest.fixture(scope="session")
def provided_value() -> int:
    return 42


class NumberService:
    async def get_number(self, number: int) -> int:
        return number


class ScopedNode(TypedDict):
    """A node with unique id per scope."""

    id: str


def get_node() -> ScopedNode:
    return {"id": uuid.uuid4().hex}


@pytest.fixture(scope="session")
def container(provided_value: int) -> aioinject.Container:
    container = aioinject.Container()
    container.register(aioinject.Object(provided_value))
    container.register(aioinject.Scoped(NumberService))
    container.register(aioinject.Scoped(get_node))
    return container
