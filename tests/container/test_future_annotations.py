from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from aioinject.containers import Container
from aioinject.providers import Scoped, Singleton


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
	class  B:
		a: A

	def get_b(a: A) -> B:
		return B(a)

	class A: ...

	cont = Container()
	cont.register(
		Singleton(A),
		Singleton(get_b) 
	)
	with cont.sync_context() as ctx:
		a = ctx.resolve(A)
		b = ctx.resolve(B)
		assert b.a is a