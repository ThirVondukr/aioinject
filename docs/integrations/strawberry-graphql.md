Aioinject integrates with `strawberry-graphql` using a
[custom extension](https://strawberry.rocks/docs/guides/custom-extensions):

```python hl_lines="10 28"
--8<-- "docs/code/integrations/strawberry-graphql.py"
```

1. Note that `inject` is imported from `aioinject.ext.strawberry`
