import contextlib
from collections.abc import AsyncIterator

from aioinject import Container
from aioinject.extensions import LifespanExtension, OnInitExtension


async def test_lifespan_extension() -> None:
    class TestExtension(LifespanExtension):
        def __init__(self) -> None:
            self.open = False
            self.closed = False

        @contextlib.asynccontextmanager
        async def lifespan(
            self,
            _: Container,
        ) -> AsyncIterator[None]:
            self.open = True
            yield
            self.closed = True

    extension = TestExtension()
    container = Container(extensions=[extension])
    assert not extension.closed
    async with container:
        assert extension.open
        assert not extension.closed
    assert extension.closed


def test_on_mount_extension() -> None:
    class TestExtension(OnInitExtension):
        def __init__(self) -> None:
            self.mounted = False

        def on_init(self, _: Container) -> None:
            self.mounted = True

    extension = TestExtension()
    assert not extension.mounted
    Container(extensions=[extension])
    assert extension.mounted
