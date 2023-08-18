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
from aioinject import inject


@inject
def awesome_function(service: Service):
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

from aioinject import Callable, Container, Inject, inject


class Service:
    pass


container = Container()
container.register(Callable(Service))


@inject
def awesome_function(
    service: Annotated[Service, Inject],
):
    print(service)


with container.sync_context() as ctx:
    service = ctx.resolve(Service)
    awesome_function()

```

## Sub dependencies

If one of your dependencies has any sub dependencies
they would be automatically provided based on class `__init__`
or function annotations

```python
from aioinject import Callable, Container


class SubDependency:
    pass


class Dependency:
    def __init__(self, sub_dependency: SubDependency):
        self.sub_dependency = sub_dependency


container = Container()
container.register(Callable(SubDependency))
container.register(Callable(Dependency))

with container.sync_context() as ctx:
    dependency = ctx.resolve(Dependency)
    print(dependency.sub_dependency)

```

If you have multiple implementations for the same dependency you can specify concrete implementation in `Inject`:

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
) -> None:
    print(github_client, gitlab_client)


with container.sync_context() as ctx:
    injectee()

```

## Working with Resources

Often you need to initialize and close a resource (file, database connection, etc...),
you can do that by using a `contextlib.(async)contextmanager` that would return your resource.

```python
import contextlib

from aioinject import Container, providers


class Session:
    pass

@contextlib.contextmanager
def get_session() -> Session:
    print("Startup")
    yield Session()
    print("Shutdown")


container = Container()
container.register(providers.Callable(get_session))

with container.sync_context() as ctx:
    session = ctx.resolve(Session) # Startup
    session = ctx.resolve(Session) # Nothing is printed, Session is cached
# Shutdown
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


async def main() -> None:
    container = Container()
    container.register(providers.Callable(get_service))

    async with container.context() as ctx:
        service = await ctx.resolve(Service)
        print(service)


if __name__ == "__main__":
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
