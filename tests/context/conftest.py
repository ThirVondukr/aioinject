import dataclasses
from typing import Annotated

import pytest

from aioinject import Callable, Container, Inject


class _A:
    pass


@dataclasses.dataclass
class _B:
    a: Annotated[_A, Inject]


@dataclasses.dataclass
class _C:
    b: Annotated[_B, Inject]


@pytest.fixture
def container():
    container = Container()
    container.register(Callable(_A))
    container.register(Callable(_B))
    container.register(Callable(_C))
    return container
