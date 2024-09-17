import dataclasses
from typing import TYPE_CHECKING, Annotated, Generic, TypeAlias, TypeVar


@dataclasses.dataclass(slots=True)
class Inject:
    pass


T = TypeVar("T")

if TYPE_CHECKING:
    Injected: TypeAlias = Annotated[T, Inject]

else:

    class Injected(Generic[T]):
        def __class_getitem__(cls, item: object) -> object:
            return Annotated[item, Inject]
