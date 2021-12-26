import functools
import inspect
import itertools
import typing
from typing import Any, Type

from dependency_depression.context import context_var
from dependency_depression.providers import collect_dependencies


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
    type_hints = typing.get_type_hints(func, include_extras=True)
    signature = inspect.signature(func)
    dependencies = list(collect_dependencies(type_hints=type_hints))

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        missing_dependencies = _missing_kwargs(type_hints, signature, *args, **kwargs)
        try:
            ctx = context_var.get()
        except LookupError:
            return func(*args, **kwargs)
        return func(
            *args,
            **kwargs,
            **{
                dep.name: ctx.resolve(
                    interface=dep.interface,
                    impl=dep.impl,
                    use_cache=dep.use_cache,
                )
                for dep in dependencies
                if dep.name in missing_dependencies
            },
        )

    return wrapper


def inject(func):
    return _wrap_sync(func)
