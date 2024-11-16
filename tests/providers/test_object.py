from aioinject import Object


async def test_would_provide_same_object() -> None:
    obj = object()
    provider = Object(object_=obj)

    assert provider.provide_sync({}) is obj
    assert await provider.provide({}) is obj


async def _async_func() -> None:
    pass


class _Class:
    pass


def test_should_not_be_async() -> None:
    for obj in [_async_func, _Class]:
        provider = Object(object_=obj)
        assert provider.is_async is False
