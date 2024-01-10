import dataclasses
from typing import Annotated

import pytest

from aioinject import Container, Inject, Scoped


class _A:
    pass


@dataclasses.dataclass
class _B:
    a: Annotated[_A, Inject]


@dataclasses.dataclass
class _C:
    b: Annotated[_B, Inject]


@pytest.fixture
def container() -> Container:
    container = Container()
    container.register(Scoped(_A))
    container.register(Scoped(_B))
    container.register(Scoped(_C))
    return container
