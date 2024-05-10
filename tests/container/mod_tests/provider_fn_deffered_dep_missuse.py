from __future__ import annotations

from aioinject.containers import Container
from aioinject.providers import Singleton


cont = Container()


# notice that C is not defined yet
def get_c() -> C:
    return C()


cont.register(Singleton(get_c))


class C: ...
