from typing import Annotated

from aioinject import Inject
from aioinject._utils import get_inject_annotations


def test_inject_annotations_returns_all_inject_markers() -> None:
    def func(
        a: int,
        b: Annotated[int, Inject],
        c: Annotated[int, Inject()],
    ) -> None:
        pass

    assert get_inject_annotations(func) == {
        "b": Annotated[int, Inject],
        "c": Annotated[int, Inject()],
    }
