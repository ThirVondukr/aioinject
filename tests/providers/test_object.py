from typing import Annotated, Any

import pytest

from dependency_depression import Inject, Object


@pytest.mark.anyio
async def test_would_provide_same_object():
    obj = object()
    provider = Object(object_=obj, type_=Any)

    assert provider.provide_sync() is obj
    assert await provider.provide() is obj


@pytest.fixture
def dependencies_test_data():
    class Test:
        def __init__(self, a: Annotated[int, Inject]):
            pass

    def test(a: Annotated[int, Inject], b: Annotated[Test, Inject]):
        pass

    return object(), Test, test


def test_should_have_no_dependencies(dependencies_test_data):
    for obj in dependencies_test_data:
        provider = Object(object_=obj, type_=Any)
        assert not provider.dependencies


def test_should_have_empty_type_hints(dependencies_test_data):
    for obj in dependencies_test_data:
        provider = Object(object_=obj, type_=Any)
        assert not provider.type_hints
