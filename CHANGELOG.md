## 0.36.0 (2025-01-09)

### Feat

- add iterable providers

### Fix

- test_partially_resolved_generic
- update get_typevars to return a list of TypeVars and enhance nested generic tests
- enhance generic type handling and add tests for nested concrete generics
- correct test to -> `test_nested_unresolved_generic`
- update resolved type handling in InjectionContext and add uv.lock for dependency management

### Refactor

- use is_iterable_generic_collection
- use Provider.__hash__ in stores

## 0.35.3 (2024-11-22)

### Fix

- avoid closing context multiple times

## 0.35.2 (2024-11-22)

### Fix

- **litestar**: exceptions weren't propagated to contextmanager dependencies

### Refactor

- **litestar**: make after_exception function private
- migrate to uv

## 0.35.1 (2024-09-24)

## 0.35.0 (2024-09-17)

### Feat

- Add `Injected[T]` annotation as a shorthand for `Annotated[T, Inject]` by @nrbnlulu

### Tests

- Add test for `strawberry.subscription` by @nrbnlulu
