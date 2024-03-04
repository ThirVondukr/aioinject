import contextlib
from collections.abc import AsyncIterator

from aioinject import Container
from aioinject.extensions import LifespanExtension


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
