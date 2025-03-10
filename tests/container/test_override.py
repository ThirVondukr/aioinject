import abc

import pytest

from aioinject import Container, Object, Transient
from tests.utils_ import maybe_async_context, maybe_await


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


class Interface(abc.ABC):
    @abc.abstractmethod
    def method(self) -> int: ...


class Impl1:
    def method(self) -> int:
        return 42


class Impl2:
    def method(self) -> int:
        return 1337


@pytest.mark.parametrize("context_method_name", ["sync_context", "context"])
async def test_iterable_provider_override(context_method_name: str) -> None:
    container = Container()
    container.register(Transient(Impl1, type_=Interface))
    container.register(Transient(Impl2, type_=Interface))
    context_method = getattr(container, context_method_name)

    async with maybe_async_context(context_method()) as ctx:
        assert len(await maybe_await(ctx.resolve_iterable(Interface))) == 2  # noqa: PLR2004

    async with maybe_async_context(context_method()) as ctx:
        with container.override(Transient(Impl1, type_=Interface)):
            assert len(await maybe_await(ctx.resolve_iterable(Interface))) == 1
