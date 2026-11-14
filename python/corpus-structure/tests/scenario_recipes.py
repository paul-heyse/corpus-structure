"""Exact recipe-type ownership for scenario builders; compositions stay with each owner."""

from collections.abc import Callable
from typing import Any

_BUILDERS: dict[type, Callable[..., Any]] = {}


def register_scenario_builder(recipe_type: type, builder: Callable[..., Any]) -> None:
    if recipe_type in _BUILDERS:
        raise ValueError(f"scenario recipe already has a builder: {recipe_type.__name__}")
    _BUILDERS[recipe_type] = builder


def scenario_builder(recipe: object) -> Callable[..., Any]:
    try:
        return _BUILDERS[type(recipe)]
    except KeyError:
        raise ValueError(f"unknown scenario recipe type: {type(recipe).__name__}") from None
