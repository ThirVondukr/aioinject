import functools
from collections.abc import Callable
from typing import ParamSpec, TypeVar


T = TypeVar("T")
P = ParamSpec("P")


def dummy_decorator(func: Callable[P, T]) -> Callable[P, T]:
    @functools.wraps(func)
    def decorator(*args: P.args, **kwargs: P.kwargs) -> T:
        return func(*args, **kwargs)

    return decorator
