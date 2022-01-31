import inspect
from typing import Any


def clear_wrapper(wrapper: Any, inject_annotations: dict[str, Any]):
    signature = inspect.signature(wrapper)
    new_params = tuple(
        p for p in signature.parameters.values() if p.name not in inject_annotations
    )
    wrapper.__signature__ = signature.replace(parameters=new_params)
    for name in inject_annotations:
        del wrapper.__annotations__[name]
    return wrapper
