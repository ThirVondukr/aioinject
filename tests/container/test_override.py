from aioinject import Container, Object


class _A:
    pass


def test_provider_override() -> None:
    a = _A()
    container = Container()
    container.register(Object(a))
    with container.sync_context() as ctx:
        assert ctx.resolve(_A) is a

        a_overridden = _A()
        assert a_overridden is not a

    with (
        container.sync_context() as ctx,
        container.override(
            Object(a_overridden),
        ),
    ):
        assert ctx.resolve(_A) is a_overridden is not a


def test_override_multiple_times() -> None:
    container = Container()
    with container.override(Object(1)):
        with container.override(Object(2)), container.sync_context() as ctx:
            assert ctx.resolve(int) == 2  # noqa: PLR2004

        with container.sync_context() as ctx:
            assert ctx.resolve(int) == 1


def test_override_batch() -> None:
    container = Container()
    container.register(Object(0))
    container.register(Object("barfoo"))

    with (
        container.override(
            Object(1),
            Object("foobar"),
        ),
        container.sync_context() as ctx,
    ):
        assert ctx.resolve(int) == 1
        assert ctx.resolve(str) == "foobar"

    with container.sync_context() as ctx:
        assert ctx.resolve(int) == 0
        assert ctx.resolve(str) == "barfoo"
