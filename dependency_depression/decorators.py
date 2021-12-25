import functools
import inspect
import itertools
import typing
from typing import Any, Type

from dependency_depression.context import context_var


def _missing_kwargs(
    type_hints: dict[str, Type],
    signature: inspect.Signature,
    *args: Any,
    **kwargs: Any,
) -> dict[str, Type]:
    already_provided_args: set[str] = set(
        itertools.islice(signature.parameters, len(args))
    )
    already_provided_args.update(kwargs)

    need_to_provide = {
        k: v for k, v in type_hints.items() if k not in already_provided_args
    }
    return need_to_provide


def _wrap_sync(func):
    type_hints = typing.get_type_hints(func)
    signature = inspect.signature(func)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        dependencies = _missing_kwargs(type_hints, signature, *args, **kwargs)
        try:
            ctx = context_var.get()
        except LookupError:
            return func(*args, **kwargs)
        return func(
            *args, **kwargs, **{k: ctx.resolve_sync(v) for k, v in dependencies.items()}
        )

    return wrapper


def inject(func):
    return _wrap_sync(func)
