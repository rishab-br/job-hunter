"""
Central registry mapping skill function names to their MCP tool equivalents.
As MCP servers are connected, register them here so agents can resolve
tool calls without hardcoding skill imports throughout the codebase.
"""

_registry: dict[str, callable] = {}


def register(name: str, fn: callable) -> None:
    _registry[name] = fn


def resolve(name: str) -> callable:
    if name not in _registry:
        raise KeyError(f"No tool registered under '{name}'")
    return _registry[name]
