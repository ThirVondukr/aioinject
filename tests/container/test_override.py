from aioinject import Container, Object


class _A:
    pass


def test_provider_override():
    a = _A()
    container = Container()
    container.register(Object(a))
    with container.sync_context() as ctx:
        assert ctx.resolve(_A, use_cache=False) is a

        a_overridden = _A()
        assert a_overridden is not a

        with container.override(Object(a_overridden)):
            assert ctx.resolve(_A, use_cache=False) is a_overridden is not a
