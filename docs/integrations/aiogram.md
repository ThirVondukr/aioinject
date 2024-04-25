Aiogram integration is achieved with `AioInjectMiddleware`, which you
could register on individual observers or
on all observers in a router via `add_to_router` method:

```python
--8<-- "docs/code/integrations/aiogram_.py"
```
