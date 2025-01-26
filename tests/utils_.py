import functools
from collections.abc import Callable
import sys
from typing import ParamSpec, TypeVar

import pytest


T = TypeVar("T")
P = ParamSpec("P")


def dummy_decorator(func: Callable[P, T]) -> Callable[P, T]:
    @functools.wraps(func)
    def decorator(*args: P.args, **kwargs: P.kwargs) -> T:
        return func(*args, **kwargs)

    return decorator


py_gte_311 = pytest.mark.skipif(
    sys.version_info < (3, 11),
    reason="This test requires Python 3.11 or later",
)
