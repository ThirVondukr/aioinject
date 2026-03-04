from __future__ import annotations

import pytest

from aioinject import Container, Scoped
from aioinject.errors import CyclicDependencyError


class A:
    def __init__(self, b: B) -> None: ...


class B:
    def __init__(self, a: A) -> None: ...


def test_cyclic_dependency() -> None:
    container = Container()
    container.register(Scoped(A), Scoped(B))
    with pytest.raises(CyclicDependencyError) as exc_info:
        container.registry.compile(A, is_async=False)

    assert str(exc_info.value) == (
        "Cyclic dependency found between:\n"
        "<class 'tests.container.test_registry.B'> - <class 'tests.container.test_registry.A'>"
    )
