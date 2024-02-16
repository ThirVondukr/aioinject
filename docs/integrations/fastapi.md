To integrate with FastAPI you need to add a `AioinjectMiddleware` and
optionally a lifespan if you use context manager dependencies:
```python hl_lines="24-25"
--8<-- "docs/code/integrations/fastapi_.py"
```
