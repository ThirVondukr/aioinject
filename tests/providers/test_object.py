from typing import Any

import pytest

from dependency_depression import Object


@pytest.mark.anyio
async def test_would_provide_same_object():
    obj = object()
    provider = Object(Any, object_=obj)

    assert provider.provide_sync() is obj
    assert await provider.provide() is obj
