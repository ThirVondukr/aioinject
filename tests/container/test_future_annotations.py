from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

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
    pass


def test_provider_fn_deffered_dep_missuse() -> None:

    with pytest.raises(ValueError) as exc_info:  # noqa: PT011
        from tests.container.mod_tests import (
            provider_fn_deffered_dep_missuse,  # noqa: F401
        )
    assert exc_info.match("Or it's type is not defined yet.")
