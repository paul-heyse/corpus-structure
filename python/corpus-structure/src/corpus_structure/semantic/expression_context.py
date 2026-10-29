"""Bind only referenced source macro definitions to expression meaning."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from corpus_structure.core import tex
from corpus_structure.core.evidence import MacroDef


def bind_expression_context(value: Any, macros: Mapping[str, MacroDef]) -> Any:
    """Return a source projection without modifying the authored observation.

    Definitions follow references transitively, including optional defaults. Unused macros do
    not split facts; cycles terminate by macro name. Scientific parsing remains a separate step.
    """
    if isinstance(value, Mapping):
        result = {key: bind_expression_context(item, macros) for key, item in value.items()}
        if result.get("kind") in {"expression", "formula", "set"} and result.get("language") in {
            "latex",
            "tex",
        }:
            pending = [
                token.text for token in tex.tokens(result["expression"]) if token.text in macros
            ]
            seen = set()
            context = {}
            while pending:
                name = pending.pop()
                if name in seen:
                    continue
                seen.add(name)
                definition = macros[name]
                entry = {
                    "kind": "plain" if definition.default is None else "optional",
                    "name": name,
                    "body": definition.body,
                    "nargs": definition.nargs,
                }
                if definition.default is not None:
                    entry["default"] = definition.default
                context[name] = entry
                pending.extend(
                    token.text
                    for text in (definition.body, definition.default or "")
                    for token in tex.tokens(text)
                    if token.text in macros
                )
            result["macro_context"] = {name: context[name] for name in sorted(context)}
        return result
    if isinstance(value, (list, tuple)):
        return tuple(bind_expression_context(item, macros) for item in value)
    return value
