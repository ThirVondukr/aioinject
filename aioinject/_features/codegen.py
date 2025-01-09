from __future__ import annotations

import collections
import dataclasses
import typing
from collections.abc import Iterator
from graphlib import TopologicalSorter
from typing import TYPE_CHECKING, Any, TypeVar

from aioinject._features.generics import (
    _is_generic_alias,
    get_generic_parameter_map,
)
from aioinject._store import NotInCache
from aioinject.providers import DependencyLifetime


if TYPE_CHECKING:
    from aioinject import InjectionContext, Provider
    from aioinject.context import _BaseInjectionContext
from aioinject.providers import Singleton


_start = """
    if ({provider_name}_instance := {provider_store}.get({provider_name})) is NotInCache.sentinel:
"""
_start_singleton = """
    async with {provider_store}.lock({provider_name}) as should_provide:
        if should_provide:
"""
_end_singleton = """
        else:
            {provider_name}_instance = {provider_store}.get({provider_name})
"""

_provide = "        {provider_name}_instance = await {provider_name}.provide({{{provider_dependencies}}})"
_provide_generator = """        {provider_name}_instance = await {provider_store}.enter_context(
            await {provider_name}.provide({{{provider_dependencies}}})
        )
"""
_save = """        {provider_store}.add({provider_name}, {provider_name}_instance)
        await self._on_resolve(provider={provider_name}, instance={provider_name}_instance)
"""
def _add_tabs(string: str, amount: int) -> str:
    return "\n".join((" " * amount) + line for line in string.splitlines())


def _make_template_str(
    provider: Provider[object],
    kwargs: dict[str, str],
) -> str:
    extra_tabs = 4 if isinstance(provider, Singleton) else 0
    parts = [
        _start_singleton.format_map(kwargs) if isinstance(provider,
                                                          Singleton) else _start.format_map(
            kwargs),
        _add_tabs(_provide_generator.format_map(
            kwargs) if provider.is_generator else _provide.format_map(kwargs),
                  extra_tabs),
        _add_tabs(_save.format_map(kwargs), extra_tabs),
        _end_singleton.format_map(kwargs) if isinstance(provider, Singleton) else "",
    ]
    return "\n".join(parts)


def walk_dependencies(
    root: Provider[object],
    context: _BaseInjectionContext[Any],
) -> Iterator[Provider[object]]:
    stack = [root]
    while stack:
        provider = stack.pop()

        dependencies = provider.collect_dependencies(
            context=context._container.type_context
        )
        generic_types_map = get_generic_parameter_map(
            provider.type_,  # type: ignore[arg-type]
            dependencies=dependencies,
        )
        for dependency in dependencies:
            for dependency_provider in context._get_providers(
                generic_types_map.get(dependency.name, dependency.inner_type)
            ):
                stack.append(dependency_provider)
                yield dependency, dependency_provider


@dataclasses.dataclass(unsafe_hash=True)
class GraphNode:
    type: type[Any]
    is_iterable: bool

def make_dag(
    provider: Provider[object],
    context: _BaseInjectionContext[Any],
) -> TopologicalSorter[GraphNode]:
    graph = collections.defaultdict(list)
    print(list(walk_dependencies(provider, context)))
    for dependency, provider in walk_dependencies(provider, context):
        dependencies = provider.collect_dependencies(
            context=context._container.type_context
        )
        generic_types_map = get_generic_parameter_map(
            provider.type_,  # type: ignore[arg-type]
            dependencies=dependencies,
        )
        graph[GraphNode(dependency.inner_type, dependency.is_iterable)].extend(
            GraphNode(generic_types_map.get(dependency.name, dependency.inner_type), is_iterable=dependency.is_iterable) for
            dependency in
            dependencies
        )
    return TopologicalSorter(graph)


def _provider_name_key(type: type[Any]) -> str:
    generic_args = typing.get_args(type)

    name = str(type.__name__)
    if _is_generic_alias(type) and any(
        not isinstance(arg, TypeVar) for arg in generic_args):
        name = name + "_" + "_".join(arg.__name__ for arg in generic_args)
    return f"provider_{name}"


def context_resolve(
    type: type[Any],
    context: InjectionContext,
) -> None:
    parts = []
    root_provider = context._get_providers(type)[0]
    order: list[GraphNode] = [
        *make_dag(context._get_providers(type)[-1], context).static_order(),
        root_provider,
    ]
    print(order)
    seen_lifetimes = set()
    for node in order:
        for provider in context._get_providers(node.type):
            seen_lifetimes.add(provider.lifetime)

    for lifetime in seen_lifetimes:
        parts.append(
            f"    store_{lifetime.name} = self._get_store({lifetime})\n"
        )
    globalns = {
        NotInCache.__name__: NotInCache,
        DependencyLifetime.__name__: DependencyLifetime,
        get_generic_parameter_map.__name__: get_generic_parameter_map,
    }

    for node in order:
        provider = context._get_providers(node.type)

        dependencies = provider.collect_dependencies(
            context._container.type_context)
        generic_types_map = get_generic_parameter_map(
            provider_type,  # type: ignore[arg-type]
            dependencies=dependencies,
        )
        dependencies_format = []
        for dep in dependencies:
            dependencies_format.append(
                f"\"{dep.name}\": {_provider_name_key(generic_types_map.get(dep.name, dep.type_))}_instance")

        provider_name = _provider_name_key(provider_type)
        globalns[provider_name] = provider
        parts.append(_make_template_str(
            provider,
            dict(
                provider_name=provider_name,
                provider_is_iterable=False,
                provider_dependencies=", ".join(dependencies_format),
                provider_store=f"store_{provider.lifetime.name}",
            )
        ))

    body = "".join(parts)
    func = f"""
async def resolve(self):
{body}
    return {_provider_name_key(type)}_instance
    """
    locals = {}
    exec(func, {**context._container.type_context, **globalns}, locals)
    print(func)
    return locals["resolve"]
