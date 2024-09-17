import dataclasses
from typing import TYPE_CHECKING, Annotated


@dataclasses.dataclass(slots=True)
class Inject:
    pass

if TYPE_CHECKING:
    type Injected[T] = Annotated[T, Inject]
else:
    class Injected[T]:
        @classmethod
        def __class_getitem__(cls, item):  # noqa: ANN206, ANN001
            return Annotated[item, Inject]
