# Dependency Depression
Async-first dependency injection library based on python type hints

## Quickstart

First let's create a class we would be injecting:

```python
class Test:
    pass
```

Then we should create instance of container and register our `Test` class in it, we would use `Callable` provider that
would simply call our class, since classes are also callables!

```python
from dependency_depression import Depression, Callable

container = Depression()
container.register(Test, Callable(Test))
```

Then we should create a context and resolve our class from it:

```python
with container.sync_context() as ctx:
    ctx.resolve(Test)
    # < __main__.Test>
```
## Injecting
To mark parameters for injection mark them with `typing.Annotated`
and `Inject` marker
```python
from typing import Annotated
from dependency_depression import Callable, Depression, Inject


def create_number() -> int:
    return 42


def create_str(number: Annotated[int, Inject]) -> str:
    return str(number)

container = Depression()
container.register(str, Callable(create_str))
container.register(int, Callable(create_number))

with container.sync_context() as ctx:
    string = ctx.resolve(str)
    print(string, type(string))
    # 42 <class 'str'>
```

## Providers

When creating a provider you should specify the type it returns,
but it can be inferred from class type or function return type:

```python
from dependency_depression import Callable

provider = Callable(int)
# Is the same as Callable(factory=int, impl=int)
assert provider.provide_sync() == 0
```

Example using factory function, `impl` is inferred from return type hint:

```python
from dependency_depression import Callable


def create_foo() -> str:
    return "foo"


provider = Callable(create_foo)
assert provider.provide_sync() == "foo"
assert provider.impl is str
```

This all comes into play when you have multiple implementations for base class and want to retrieve individual providers
from a container,  
let's register two concrete classes under same interface:

```python
from dependency_depression import Depression, Callable


class Base:
    pass


class ConcreteA(Base):
    pass


class ConcreteB(Base):
    pass


container = Depression()
container.register(Base, Callable(ConcreteA))
container.register(Base, Callable(ConcreteB))

with container.sync_context() as ctx:
    a = ctx.resolve(Base, ConcreteA)  # <__main__.ConcreteA>
    b = ctx.resolve(Base, ConcreteB)  # <__main__.ConcreteB>
    
    # This would raise an error since we have two classes registered as `Base`
    ctx.resolve(Base)
```
If you have multiple classes registered under same interface
you can specify concrete class using `Impl` marker:
```python
from typing import Annotated
from dependency_depression import Inject, Impl


class Injectee:
    def __init__(
        self,
        a: Annotated[Base, Inject, Impl[ConcreteA]],
        b: Annotated[Base, Inject, Impl[ConcreteB]],
    ):
        pass
```
You can also just register concrete classes instead: 
```python
container.register(ConcreteA, Callable(ConcreteA))
container.register(ConcreteB, Callable(ConcreteB))

class Injectee:
    def __init__(
        self,
        a: Annotated[ConcreteA, Inject],
        b: Annotated[ConcreteB, Inject],
    ):
        pass
```
### Generics
Dependency Depression can also be used with Generics:
```python
import dataclasses
from typing import Generic, TypeVar, Annotated

from dependency_depression import Inject, Depression, Callable

T = TypeVar("T")


@dataclasses.dataclass
class User:
    id: int
    username: str


@dataclasses.dataclass
class Item:
    id: int
    title: str


class IRepository(Generic[T]):
    def get(self, identity: int) -> T:
        raise NotImplementedError


class UserRepository(IRepository[User]):
    def get(self, identity: int) -> User:
        return User(id=identity, username="Username")

    
class ItemRepository(IRepository[Item]):
    def get(self, identity: int) -> Item:
        return Item(id=identity, title="Title")

    
class Injectee:
    def __init__(
        self,
        user_repository: Annotated[IRepository[User], Inject],
        item_repository: Annotated[IRepository[Item], Inject],
    ):
        self.user_repository = user_repository
        self.item_repository = item_repository


container = Depression()
container.register(IRepository[User], Callable(UserRepository))
container.register(IRepository[Item], Callable(ItemRepository))
container.register(Injectee, Callable(Injectee))

with container.sync_context() as ctx:
    injectee = ctx.resolve(Injectee)
    injectee.user_repository
    # < __main__.UserRepository>
    injectee.item_repository
    # <__main__.ItemRepository>
```

## Context
Context as meant to be used within application or request scope,
it keeps instances cache and an `ExitStack` to close all resources.
### Cache
Context keeps cache of all instances, so they won't be created again,
unless `use_cache=False` or `NoCache` is used.

In this example passing `use_cache=False` would cause context to create
instance of `Test` again, however it wouldn't be cached:
```python
from dependency_depression import Callable, Depression


class Test:
    pass


container = Depression()
container.register(Test, Callable(Test))

with container.sync_context() as ctx:
    first = ctx.resolve(Test)
    
    assert first is not ctx.resolve(Test, use_cache=False)
    # first is still cached in context
    assert first is ctx.resolve(Test)
```

### Closing resources using context managers
Context would also use functions decorated with 
`contextlib.contextmanager` or `contextlib.asyncontextmanager`, 
but it won't use other instances of `ContextManager`.  
Note that you're not passing `impl` parameter should specify return type using `Iterable`, `Generator`
or their async counterparts - `AsyncIterable`and `AsyncGenerator`:

```python
import contextlib
from typing import Iterable

from dependency_depression import Depression, Callable


@contextlib.contextmanager
def contextmanager() -> Iterable[int]:
    yield 42


class ContextManager:
    def __enter__(self):
        # This would never be called
        raise ValueError

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


container = Depression()

# Without return type hint you can specify impl parameter:
# container.register(int, Callable(contextmanager, int))
container.register(int, Callable(contextmanager))
container.register(ContextManager, Callable(ContextManager))

with container.sync_context() as ctx:
    number = ctx.resolve(int)  # 42
    ctx_manager = ctx.resolve(ContextManager) # __enter__ would not be called
    with ctx_manager:
        ...
        # Oops, ValueError raised
```

In case you need to manage lifecycle of your objects
you should wrap them in a context manager:

```python
import contextlib
from typing import AsyncGenerator

from dependency_depression import Callable, Depression
from sqlalchemy.ext.asyncio import AsyncSession


@contextlib.asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    session = AsyncSession()
    async with session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

container = Depression()
container.register(AsyncSession, Callable(AsyncSession))
```

## @Inject decorator
 
`@inject` decorator allows you to automatically inject parameters
into functions:
```python
from typing import Annotated

from dependency_depression import Callable, Depression, Inject, inject


@inject
def injectee(number: Annotated[int, Inject]):
    return number


container = Depression()
container.register(int, Callable(int))

with container.sync_context():
    print(injectee())
    # 0
```
Without active context `number` parameter would not be injected:
```python
injectee()
# TypeError: injectee() missing 1 required positional argument: 'number'
```
But you still can use your function just fine
```python
print(injectee(42))
```
You can pass parameters even if you have an active context:
```python
with container.sync_context():
    print(injectee())  # 0, injected
    print(injectee(42))  # 42, provided by user
```
