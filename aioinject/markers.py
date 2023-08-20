from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Inject:
    impl: Any | None = None
    cache: bool = True
