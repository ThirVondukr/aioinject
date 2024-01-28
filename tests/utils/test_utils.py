from typing import Annotated

from aioinject import Inject
from aioinject._utils import get_inject_annotations


def test_inject_annotations_returns_all_inject_markers() -> None:
    def func(
        a: int,  # noqa: ARG001
        b: Annotated[int, Inject],  # noqa: ARG001
        c: Annotated[int, Inject()],  # noqa: ARG001
    ) -> None:
        pass

    assert get_inject_annotations(func) == {
        "b": Annotated[int, Inject],
        "c": Annotated[int, Inject()],
    }
