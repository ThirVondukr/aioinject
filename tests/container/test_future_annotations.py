from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from aioinject import Singleton
from aioinject.containers import Container
from aioinject.providers import Scoped


async def test_deffered_dependecies() -> None:
    if TYPE_CHECKING:
        from decimal import Decimal

    def some_deffered_type() -> Decimal:
        from decimal import Decimal

        return Decimal("1.0")

    class DoubledDecimal:
        def __init__(self, decimal: Decimal) -> None:
            self.decimal = decimal * 2

    container = Container()

    def register_decimal_scoped() -> None:
        from decimal import Decimal

        container.register(Scoped(some_deffered_type, Decimal))

    register_decimal_scoped()
    container.register(Scoped(DoubledDecimal))
    async with container.context() as ctx:
        assert (await ctx.resolve(DoubledDecimal)).decimal == DoubledDecimal(
            some_deffered_type(),
        ).decimal


def test_provider_fn_with_deffered_dep() -> None:
    @dataclass
    class B:
        a: A

    def get_b(a: A) -> B:
        return B(a)

    class A: ...

    cont = Container()
    cont.register(Singleton(A), Singleton(get_b))
    with cont.sync_context() as ctx:
        a = ctx.resolve(A)
        b = ctx.resolve(B)
        assert b.a is a


def test_provider_fn_deffered_dep_globals() -> None:

    def get_c(_: D) -> C:
        return C()

    class D: ...

    cont = Container()
    cont.register(Singleton(D))
    cont.register(Singleton(get_c))
    with cont.sync_context() as ctx:
        _ = ctx.resolve(D)
        _ = ctx.resolve(C)


class C: ...


def test_provider_fn_deffered_dep_missuse() -> None:
    cont = Container()

    def get_a() -> A:
        return A()

        # notice that A is not defined yet

    with pytest.raises(NameError) as exc_info:
        cont.register(Singleton(get_a))
    assert exc_info.match("name 'A' is not defined")

    class A: ...
