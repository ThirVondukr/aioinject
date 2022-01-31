Async-first dependency injection library based on python type hints

## Quickstart

First let's create a class we would be injecting:

```python
class Service:
    pass
```

Then we should create instance of container and register `Service` class in it using a provider:

```python
from aioinject import Container, providers

container = Container()
container.register(providers.Callable(Service))
```

Then we can create a context and resolve our `Service` class from it:

```python
with container.sync_context() as ctx:
    service = ctx.resolve(Service)
```

If you need to inject something into a function just annotate it with inject:

```python
from typing import Annotated
from aioinject import Inject, inject


@inject
def awesome_function(
    service: Annotated[Service, Inject],
):
    print(service)
```

And call it within an active context:

```python
with container.sync_conext() as ctx:
    awesome_function()
```

Complete example (should run as-is):

```python
from typing import Annotated

from aioinject import Container, Inject, inject, providers


class Service:
    pass


container = Container()
container.register(providers.Callable(Service))


@inject
def awesome_function(
    service: Annotated[Service, Inject],
):
    print(service)


with container.sync_context() as ctx:
    service = ctx.resolve(Service)
    awesome_function()

```

## Specifying Dependencies

To mark parameters for injection we can use `typing.Annotated`
and `Inject` marker

```python
from typing import Annotated
from aioinject import Callable, Container, Inject


class Session:
    pass


class Service:
    def __init__(
        self,
        session: Annotated[Session, Inject],
    ):
        self.session = session


container = Container()
container.register(Callable(Session))
container.register(Callable(Service))

with container.sync_context() as ctx:
    service = ctx.resolve(Service)
```

If you have multiple dependencies with same type you can specify concrete implementation in `Inject`:

```python
import dataclasses
from typing import Annotated

from aioinject import Container, providers, inject, Inject


@dataclasses.dataclass
class Client:
    name: str


def get_github_client() -> Client:
    return Client(name="GitHub Client")


def get_gitlab_client() -> Client:
    return Client(name="GitLab Client")


container = Container()
container.register(providers.Callable(get_github_client))
container.register(providers.Callable(get_gitlab_client))


@inject
def injectee(
    github_client: Annotated[Client, Inject(get_github_client)],
    gitlab_client: Annotated[Client, Inject(get_gitlab_client)],
):
    print(github_client, gitlab_client)


with container.sync_context() as ctx:
    # Manually resolving client
    client = ctx.resolve(Client, impl=get_github_client)
    print(client)
    injectee()
```

## Working with Resources

Often you need to initialize and close a resource (file, database session, etc...),
you can do that by using a `contextmanager` that would return your resource.  
We would use custom `Session` class that defines `__exit__` and `__enter__` methods:

```python
import contextlib

from aioinject import Container, providers


class Session:
    def __init__(self):
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.closed = True


@contextlib.contextmanager
def get_session() -> Session:
    with Session() as session:
        yield session


container = Container()
container.register(providers.Callable(get_session))

with container.sync_context() as ctx:
    session = ctx.resolve(Session)
    print(session.closed)
print(session.closed)  # <- Session.__exit__ would be called when context closes
```

## Async Dependencies
You can register async resolvers the same way as you do with other dependencies,
all you need to change is to use `Container.context` instead of `Container.sync_context`:

```python
import asyncio

from aioinject import Container, providers


class Service:
    pass


async def get_service() -> Service:
    await asyncio.sleep(1)
    return Service()


async def main():
    container = Container()
    container.register(providers.Callable(get_service))

    async with container.context() as ctx:
        service = await ctx.resolve(Service)
        print(service)


if __name__ == '__main__':
    asyncio.run(main())
```

## Providers

When creating a provider you should specify the type it returns, but it can be inferred from class type or function
return type:

### Callable

`Callable` provider would create instance of a class each time:

```python
from aioinject import Callable


class Service:
    pass


provider = Callable(Service)
service_one = provider.provide_sync()
service_two = provider.provide_sync()
print(service_one is service_two)
# False
```

### Singleton

`Singleton` works the same way as `Callable` but it caches first created object:

```python
from aioinject import Singleton


class Service:
    pass


provider = Singleton(Service)
first = provider.provide_sync()
second = provider.provide_sync()
print(first is second)
# True

```

### Object

`Object` provider just returns an object provided to it:

```python
from aioinject import Object


class Service:
    pass


provider = Object(Service())
service = provider.provide_sync()
print(service)
# <__main__.Service>
```
