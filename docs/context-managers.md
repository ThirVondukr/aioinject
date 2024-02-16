Dependencies can use 
[`@contextlib.contextmanager`](https://docs.python.org/3/library/contextlib.html#contextlib.contextmanager)
and [`@contextlib.asynccontextmanager`](https://docs.python.org/3/library/contextlib.html#contextlib.asynccontextmanager)
decorators to execute code during their init and shutdown.

## Implementation
Internally aioinject uses [contextlib.ExitStack](https://docs.python.org/3/library/contextlib.html#contextlib.ExitStack)
and [contextlib.AsyncExitStack](https://docs.python.org/3/library/contextlib.html#contextlib.AsyncExitStack)

## Providers
### Scoped and Transient providers
For `Scoped` and `Transient` providers dependencies will close when context is
closed:

```python
--8<-- "docs/code/contextmanagers/01_context.py"
```

### Singleton provider
In case of a `Singleton` they're closed when you close container itself:

```python
--8<-- "docs/code/contextmanagers/02_container.py"
```

## Using your own or 3rd party class as a context manager
Even if your class has `__enter__` and `__exit__` methods it won't implicitly be
used as a context manager:

```python
--8<-- "docs/code/contextmanagers/03_implicity.py"
```
Nothing is printed! You have to explicitly create a function and decorate it with
contextlib decorator:

```python
@contextlib.contextmanager
def create_class() -> Class:
    with Class() as cls:
        yield cls
```
