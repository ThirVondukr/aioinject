import dataclasses
import inspect
from inspect import Parameter
from typing import Annotated

from aioinject import Inject
from aioinject.ext.strawberry import inject


class _A:
    pass


@dataclasses.dataclass
class _B:
    a: Annotated[Inject, _A]


def dependant(
    arg: int,  # noqa: ARG001
    a: Annotated[_A, Inject],
    b: Annotated[_B, Inject],
) -> tuple[_A, _B]:
    return a, b


def test_should_remove_parameters_from_signature() -> None:
    wrapped = inject(dependant)
    signature = inspect.signature(wrapped)
    assert len(signature.parameters) == 1
    expected = {
        "arg": Parameter(
            name="arg",
            annotation=int,
            kind=Parameter.POSITIONAL_OR_KEYWORD,
        ),
    }
    assert signature.parameters == expected
