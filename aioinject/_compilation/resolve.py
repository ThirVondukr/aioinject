from __future__ import annotations

import collections
import dataclasses
import typing
from collections.abc import Iterator, Mapping, Sequence
from types import GenericAlias
from typing import TYPE_CHECKING, Any, Generic, TypeAlias, TypeVar

from aioinject._compilation.naming import make_dependency_name
from aioinject._types import (
    T,
    is_generic_alias,
    is_iterable_generic_collection,
)
from aioinject.context import ProviderRecord
from aioinject.errors import ProviderNotFoundError
from aioinject.providers.context import FromContext
from aioinject.providers.scoped import Transient
from aioinject.scope import BaseScope, CurrentScope


if TYPE_CHECKING:
    from aioinject.container import Registry
from aioinject.extensions.providers import Dependency


V = TypeVar("V")
Graph: TypeAlias = Mapping[V, Sequence[V]]


@dataclasses.dataclass(slots=True, kw_only=True)
class BoundDependency(Generic[T]):
    variable_name: str
    name: str
    type_: type[T]
    provider: ProviderRecord[T]


@dataclasses.dataclass(slots=True, kw_only=True)
class ProviderNode:
    name: str
    type_: GenericAlias | type[Any]
    provider: ProviderRecord[object]
    dependencies: tuple[BoundDependency[object], ...]

    def __hash__(self) -> int:
        return hash((self.name, False))


@dataclasses.dataclass(slots=True, kw_only=True)
class IterableNode:
    name: str
    type_: type[Any]
    inner_type: type[Any]
    dependencies: tuple[BoundDependency[object], ...]

    def __hash__(self) -> int:
        return hash((self.name, True))


@dataclasses.dataclass(slots=True, kw_only=True)
class FromContextNode:
    name: str
    type_: type[Any]
    scope: BaseScope | CurrentScope
    dependencies: tuple[BoundDependency[object], ...] = ()

    def __hash__(self) -> int:
        return hash((self.name, self.type_, self.scope))


AnyNode = ProviderNode | IterableNode | FromContextNode


def _get_orig_bases(
    type_: GenericAlias | type[Any],
) -> tuple[type, ...] | None:
    return getattr(type_, "__orig_bases__", None)


def generic_args_map(  # noqa: C901
    type_: GenericAlias | type[Any],
) -> dict[str, type[object]]:
    if is_generic_alias(type_):
        if not (parameters := getattr(type_.__origin__, "__parameters__", ())):
            return {}  # pragma: no cover

        params: dict[str, Any] = {
            param.__name__: param for param in parameters
        }
        return dict(zip(params, type_.__args__, strict=True))

    args_map = {}
    if orig_bases := _get_orig_bases(type_):
        # find the generic parent
        for base in orig_bases:
            if is_generic_alias(base):  # noqa: SIM102
                if params := {
                    param.__name__: param
                    for param in getattr(base.__origin__, "__parameters__", ())
                }:
                    args_map.update(
                        dict(zip(params, base.__args__, strict=True)),
                    )
    return args_map


def get_generic_arguments(type_: Any) -> list[typing.TypeVar] | None:
    """
    Returns generic arguments of given class, e.g. Class[T] would return [~T]
    """
    if is_generic_alias(type_):
        args = typing.get_args(type_)
        return [arg for arg in args if isinstance(arg, typing.TypeVar)]
    return None


def get_generic_parameter_map(
    provided_type: GenericAlias | type[Any],
    dependencies: Sequence[Dependency[Any]],
) -> dict[str, type[object]]:
    args_map = generic_args_map(provided_type)
    if not args_map:
        return {}

    result = {}
    for dependency in dependencies:
        inner_type = dependency.type_
        if dependency.type_.__name__ in args_map:
            result[dependency.name] = args_map[dependency.type_.__name__]

        if generic_arguments := get_generic_arguments(inner_type):
            # This is a generic type, we need to resolve the type arguments
            # and pass them to the provider.
            resolved_args = tuple(
                args_map[arg.__name__] for arg in generic_arguments
            )
            result[dependency.name] = inner_type[resolved_args]
    return result


def _resolve_provider_node_dependencies(
    type_: GenericAlias | type[Any],
    node_name: str,
    provider: ProviderRecord[object],
    registry: Registry,
) -> tuple[BoundDependency[Any], ...]:
    generic_args_map = get_generic_parameter_map(
        provided_type=type_,
        dependencies=provider.info.dependencies,
    )

    dependencies = []
    for provider_dependency in provider.info.dependencies:
        is_iterable = is_iterable_generic_collection(provider_dependency.type_)

        bound_dependency_type = generic_args_map.get(
            provider_dependency.name, provider_dependency.type_
        )
        dependency_type = (
            provider_dependency.type_ if is_iterable else bound_dependency_type
        )

        dependency_provider = registry.get_provider(
            typing.get_args(bound_dependency_type)[0]
            if is_iterable
            else dependency_type
        )
        dependency_args_map = get_generic_parameter_map(
            bound_dependency_type, dependency_provider.info.dependencies
        )
        resolved_type = (
            dependency_args_map.get(
                provider_dependency.name,
                dependency_type
                if is_generic_alias(dependency_type)
                else dependency_provider.info.type_,
            )
            if not is_iterable
            else dependency_type
        )
        variable_name = make_dependency_name(resolved_type)  # type: ignore[arg-type]

        if isinstance(dependency_provider.provider, Transient):
            variable_name = (
                f"{node_name}_{provider_dependency.name}_{variable_name}"
            )
        if isinstance(dependency_provider.provider, FromContext):
            scope_name = (
                provider.info.scope.name
                if isinstance(dependency_provider.provider.scope, CurrentScope)
                else dependency_provider.provider.scope.name
            )
            variable_name = f"{make_dependency_name(provider_dependency.type_)}_scope_{scope_name}"

        dependency = BoundDependency(
            variable_name=variable_name,
            name=provider_dependency.name,
            type_=resolved_type,  # type: ignore[arg-type]
            provider=dependency_provider,
        )
        dependencies.append(dependency)

    return tuple(dependencies)


def _resolve_node(
    type_: type[Any],
    name: str,
    registry: Registry,
    dependant: ProviderNode | None = None,
) -> AnyNode:
    try:
        provider = registry.get_provider(type_)
    except ProviderNotFoundError:
        if not is_iterable_generic_collection(type_):  # pragma: no cover
            raise

        inner_type = typing.get_args(type_)[0]
        providers = registry.get_providers(inner_type)

        return IterableNode(
            type_=type_,
            inner_type=inner_type,
            name=name,
            dependencies=tuple(
                BoundDependency(
                    name=make_dependency_name(provider.info.type_),
                    variable_name=make_dependency_name(provider.info.type_),
                    type_=provider.info.type_,
                    provider=provider,
                )
                for provider in providers
            ),
        )
    resolved_type: GenericAlias | type[Any] = (
        provider.info.type_ if type_ == provider.info.interface else type_
    )

    if isinstance(provider.provider, FromContext):
        scope = provider.provider.scope
        if dependant and isinstance(scope, CurrentScope):
            scope = dependant.provider.info.scope
            name = f"{make_dependency_name(type_)}_scope_{scope.name}"

        return FromContextNode(
            name=name,
            scope=scope,
            type_=type_,
        )

    return ProviderNode(
        type_=resolved_type,
        name=name,
        provider=provider,
        dependencies=_resolve_provider_node_dependencies(
            type_=resolved_type,
            node_name=name,
            provider=provider,
            registry=registry,
        ),
    )


def resolve_dependencies(  # noqa: C901
    root_type: type[Any],
    registry: Registry,
) -> Iterator[AnyNode]:
    stack = [
        _resolve_node(
            root_type, name=make_dependency_name(root_type), registry=registry
        )
    ]
    seen = set()
    while stack:
        node = stack.pop()
        if node in seen:
            continue

        seen.add(node)

        yield node

        match node:
            case ProviderNode():
                generic_args_map = get_generic_parameter_map(
                    node.type_, node.provider.info.dependencies
                )
                for dependency in node.dependencies:
                    orig_dependency = next(
                        dep
                        for dep in node.provider.info.dependencies
                        if dep.name == dependency.name
                    )
                    dependency_type = generic_args_map.get(
                        dependency.name, orig_dependency.type_
                    )
                    stack.append(
                        _resolve_node(
                            type_=dependency_type,
                            name=dependency.variable_name,
                            registry=registry,
                            dependant=node,
                        )
                    )

            case IterableNode():
                providers = registry.get_providers(node.inner_type)
                for provider in providers:
                    new_node = ProviderNode(
                        provider=provider,
                        name=make_dependency_name(provider.info.type_),
                        type_=provider.info.type_,
                        dependencies=_resolve_provider_node_dependencies(
                            type_=node.type_,
                            node_name=node.name,
                            provider=provider,
                            registry=registry,
                        ),
                    )
                    stack.append(new_node)
            case FromContextNode():
                pass
            case _:  # pragma: no cover
                typing.assert_never(node)  # type: ignore[unreachable]


def create_graph(
    nodes: Sequence[AnyNode],
) -> Graph[type[object] | GenericAlias]:
    graph: dict[
        type[object] | GenericAlias, list[type[object | GenericAlias]]
    ] = collections.defaultdict(list)
    for node in nodes:
        graph[node.type_].extend(dep.type_ for dep in node.dependencies)
    return graph


def sort_graph(graph: Graph[V]) -> Sequence[V]:  # noqa: C901
    indegree = collections.defaultdict(int)
    for node in graph:
        indegree[node] = 0
    for dependencies in graph.values():
        for dependency in dependencies:
            indegree[dependency] += 1

    result = []
    stack = collections.deque(
        [node for (node, degree) in indegree.items() if degree == 0]
    )
    while stack:
        node = stack.popleft()
        result.append(node)
        for dependency in graph[node]:
            indegree[dependency] -= 1
            if indegree[dependency] == 0:
                stack.append(dependency)
    return result


def find_scss(graph: Graph[V]) -> Sequence[Sequence[V]]:  # noqa: C901
    index = {}
    lowlink = {}
    stack: list[V] = []
    on_stack: set[V] = set()
    result: list[list[V]] = []

    index_counter = 0

    def strongconnect(v: V) -> None:  # noqa: C901
        nonlocal index_counter
        index[v] = lowlink[v] = index_counter
        index_counter += 1
        stack.append(v)
        on_stack.add(v)

        for w in graph.get(v, ()):
            if w not in index:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in on_stack:
                lowlink[v] = min(lowlink[v], index[w])

        if lowlink[v] == index[v]:
            component: list[V] = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                component.append(w)
                if w == v:
                    break
            result.append(component)

    for node in graph:
        if node not in index:
            strongconnect(node)

    return result
