import dataclasses
from typing import Any, TypeVar

_T = TypeVar("_T")


@dataclasses.dataclass
class Inject:
    impl: Any = None
    cache: bool = True
