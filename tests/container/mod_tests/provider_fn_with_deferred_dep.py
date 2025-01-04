from __future__ import annotations

from dataclasses import dataclass

from aioinject.containers import Container
from aioinject.providers import Singleton


@dataclass
class B:
    a: A


cont = Container()


def get_b(a: A) -> B:
    return B(a)


cont.register(Singleton(get_b))


class A: ...


cont.register(Singleton(A))
with cont.sync_context() as ctx:
    a = ctx.resolve(A)
    b = ctx.resolve(B)
    assert b.a is a
