from typing import Annotated, Any

import pytest

from aioinject import Inject, Object


@pytest.mark.anyio
async def test_would_provide_same_object() -> None:
    obj = object()
    provider = Object(object_=obj)

    assert provider.provide_sync({}) is obj
    assert await provider.provide({}) is obj


@pytest.fixture
def dependencies_test_data() -> tuple[Any, ...]:
    class Test:
        def __init__(
            self,
            a: Annotated[int, Inject],
        ) -> None:
            pass

    def test(
        a: Annotated[int, Inject],  # noqa: ARG001
        b: Annotated[Test, Inject],  # noqa: ARG001
    ) -> None:
        pass

    return object(), Test, test


def test_should_have_no_dependencies(
    dependencies_test_data: tuple[Any, ...],
) -> None:
    for obj in dependencies_test_data:
        provider = Object(object_=obj)
        assert not provider.resolve_dependencies()


def test_should_have_empty_type_hints(
    dependencies_test_data: tuple[Any, ...],
) -> None:
    for obj in dependencies_test_data:
        provider = Object(object_=obj)
        assert not provider.type_hints


def test_should_not_be_async(
    dependencies_test_data: tuple[Any, ...],
) -> None:
    for obj in dependencies_test_data:
        provider = Object(object_=obj)
        assert provider.is_async is False
