Async-first dependency injection library based on python type hints


## Framework integrations:
- [FastAPI](/examples/fastapi.md)
- [Litestar](/examples/litestar.md)
- [Strawberry-Graphql](/examples/strawberry-graphql.md)


## Installation
Install using pip `pip install aioinject`

## Example

```python
import aioinject


class Database:
    def __init__(self) -> None:
        self._storage = {1: "Username"}

    def get(self, id: int) -> str | None:
        return self._storage.get(id)


class UserService:
    def __init__(self, database: Database) -> None:
        self._database = database

    def get(self, id: int) -> str:
        user = self._database.get(id)
        if user is None:
            raise ValueError
        return user


container = aioinject.Container()
container.register(aioinject.Singleton(Database))
container.register(aioinject.Singleton(UserService))


def main() -> None:
    with container.sync_context() as ctx:
        service = ctx.resolve(UserService)
        user = service.get(1)
        assert user == "Username"
        print(user)


if __name__ == "__main__":
    main()
```

## Injecting dependencies into a function
You can inject dependencies into a function using `@inject` decorator,
but that's usually only necessary if you're working with a framework:
```py
import contextlib
from collections.abc import AsyncIterator
from contextlib import aclosing
from typing import Annotated

import uvicorn
from fastapi import FastAPI

from aioinject import Container, Inject, Singleton
from aioinject.ext.fastapi import AioInjectMiddleware, inject


class Service:
    pass


container = Container()
container.register(Singleton(Service))


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with aclosing(container):
        yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(AioInjectMiddleware, container=container)


@app.get("/")
@inject
async def root(service: Annotated[Service, Inject]) -> str:
    return str(service)


if __name__ == "__main__":
    uvicorn.run("main:app")
```


## Using multiple dependencies with same type

If you have multiple implementations for the same dependency
you can use `typing.NewType` to differentiate between them:

```python
import dataclasses
from typing import Annotated, NewType

from aioinject import Container, providers, inject, Inject


@dataclasses.dataclass
class Client:
    name: str


GitHubClient = NewType("GitHubClient", Client)

GitLabClient = NewType("GitLabClient", Client)


def get_github_client() -> GitHubClient:
    return GitHubClient(Client(name="GitHub Client"))


def get_gitlab_client() -> GitLabClient:
    return GitLabClient(Client(name="GitLab Client"))


container = Container()
container.register(providers.Scoped(get_github_client))
container.register(providers.Scoped(get_gitlab_client))

with container.sync_context() as ctx:
    github_client = ctx.resolve(GitHubClient)
    gitlab_client = ctx.resolve(GitLabClient)

    print(github_client, gitlab_client)
```

## Working with Resources

Often you need to initialize and close a resource (file, database connection, etc...),
you can do that by using a `contextlib.(async)contextmanager` that would return your resource. 
Aioinject would automatically close them when `context` is closed,
or when you call `container.aclose()` if your dependency is a `Singleton`.

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
container.register(providers.Scoped(get_session))

with container.sync_context() as ctx:
    session = ctx.resolve(Session)  # Startup
    session = ctx.resolve(Session)  # Nothing is printed, Session is cached
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
    container.register(providers.Scoped(get_service))

    async with container.context() as ctx:
        service = await ctx.resolve(Service)
        print(service)


if __name__ == "__main__":
    asyncio.run(main())
```

## Providers

When creating a provider you should specify the type it returns, but it can be inferred from class type or function
return type:

### Scoped

`Scoped` (or `Factory` for convenience) provider would create instance of a class each time:

```python
from aioinject import Scoped


class Service:
    pass


provider = Scoped(Service)
service_one = provider.provide_sync()
service_two = provider.provide_sync()
print(service_one is service_two)
# False
```

### Singleton

`Singleton` works the same way as `Scoped` but it caches first created object:

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
