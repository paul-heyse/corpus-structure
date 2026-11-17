"""Mutable-premise checks for an already authenticated closed Python slice."""

from __future__ import annotations

import copyreg
import dataclasses
import inspect
import sys
from collections.abc import Callable
from functools import cached_property
from types import FunctionType, ModuleType
from typing import Any, cast

from .file_custody import FileCustody


@dataclasses.dataclass(frozen=True, eq=False)
class _Identity:
    value: Any

    def __eq__(self, other):
        return isinstance(other, _Identity) and self.value is other.value


def _state(value):
    """Snapshot literals deeply; other objects retain actual reference identity."""
    if isinstance(value, _Identity):
        return value
    if type(value) in (str, bytes, int, float, bool, type(None)):
        return type(value), value
    if type(value) in (tuple, list):
        return type(value), tuple(_state(item) for item in value)
    if type(value) is dict:
        return dict, tuple((key, _state(item)) for key, item in value.items())
    if type(value) in (set, frozenset):
        return type(value), frozenset(value)
    if isinstance(value, dataclasses.Field):
        return tuple(_state(getattr(value, name)) for name in value.__slots__)
    return _Identity(value)


class AuthenticatedSlice:
    """Retained correspondence plus file and runtime-object invalidation checks.

    The caller must run its complete owning verifier before construction. This
    class confers neither acquisition nor operation/publication authority.
    """

    def __init__(self, files: tuple[FileCustody, ...], modules, members, globals):
        self.files = files
        self._checks: list[tuple[Callable[[], Any], Any]] = []
        seen = set()

        def remember(getter):
            value = getter()
            self._checks.append((getter, _state(value)))
            if isinstance(value, FunctionType) and value.__module__ in modules:
                function(value)
            elif isinstance(value, type) and value.__module__ in modules:
                owner(value)
            elif isinstance(value, (staticmethod, classmethod)):
                function(value.__func__)
            elif isinstance(value, property):
                for accessor in (value.fget, value.fset, value.fdel):
                    if accessor is not None:
                        function(accessor)
            elif isinstance(value, cached_property):
                function(value.func)
            elif isinstance(value, dataclasses.Field):
                for name in value.__slots__:
                    remember(lambda value=value, name=name: getattr(value, name))
            elif type(value) in (dict, tuple, list):
                if id(value) in seen:
                    return
                seen.add(id(value))
                keys = tuple(value) if type(value) is dict else range(len(value))
                for key in keys:
                    remember(lambda value=value, key=key: value[key])

        def function(value):
            if id(value) in seen:
                return
            seen.add(id(value))
            for name in (
                "__code__",
                "__globals__",
                "__builtins__",
                "__defaults__",
                "__kwdefaults__",
                "__annotations__",
                "__dict__",
                "__name__",
                "__qualname__",
                "__module__",
            ):
                if name in {"__globals__", "__builtins__"}:

                    def getter(value=value, name=name):
                        return _Identity(getattr(value, name))

                    self._checks.append((getter, getter()))
                else:
                    remember(lambda value=value, name=name: getattr(value, name))
            from .data_operation_ports import _code_globals

            for name in _code_globals(value.__code__):

                def getter(value=value, name=name):
                    return value.__globals__.get(name, value.__builtins__.get(name))

                self._checks.append((getter, _state(getter())))
            cells = tuple(value.__closure__ or ())
            self._checks.append((lambda value=value: tuple(value.__closure__ or ()), _state(cells)))
            for cell in cells:
                remember(lambda cell=cell: cell.cell_contents)

        def owner(value):
            if id(value) in seen or value.__module__ == "builtins":
                return
            seen.add(id(value))
            # Python 3.14 may materialize the class annotations on first access;
            # this is preparation, not an observed runtime mutation.
            getattr(value, "__annotations__", None)
            if dataclasses.is_dataclass(value):
                # deepcopy/pickle lazily cache this standard class fact. Prepare
                # it before fixing the class dictionary, then protect the cache
                # together with the already authenticated generated behavior.
                slotnames = cast(Callable[[type], list[str]], vars(copyreg)["_slotnames"])
                slotnames(value)
            self._checks.append(
                (lambda value=value: tuple(vars(value)), _state(tuple(vars(value))))
            )
            for name in ("__name__", "__qualname__", "__module__"):
                remember(lambda value=value, name=name: getattr(value, name))
            remember(lambda value=value: value.__bases__)
            for name in tuple(vars(value)):
                remember(lambda value=value, name=name: inspect.getattr_static(value, name))

        for name, module in modules.items():
            self._checks.append((lambda name=name: sys.modules.get(name), _Identity(module)))
            # A dotted import is also a binding on each parent module.
            parts = name.split(".")
            for index in range(1, len(parts)):
                parent = sys.modules.get(".".join(parts[:index]))
                child = parts[index]
                if isinstance(parent, ModuleType):
                    remember(lambda parent=parent, child=child: vars(parent).get(child))
        for getter in members:
            remember(getter)
        for module, name, fallback in globals:
            remember(
                lambda module=module, name=name, fallback=fallback: vars(module).get(name, fallback)
            )

    def check(self):
        for record in self.files:
            record.check()
        for getter, expected in self._checks:
            try:
                actual = _state(getter())
            except (AttributeError, KeyError, ValueError) as error:
                raise ValueError("authenticated runtime slice changed; restart required") from error
            if actual != expected:
                raise ValueError("authenticated runtime slice changed; restart required")
