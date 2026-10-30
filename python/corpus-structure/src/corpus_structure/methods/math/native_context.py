"""Operation-local native premises; neither source nor references consult ambient facts."""

from __future__ import annotations

import hashlib
import importlib
import json
from dataclasses import dataclass, field
from functools import cached_property
from types import FunctionType, MappingProxyType
from typing import Any

import sympy
from sympy.assumptions import AssumptionsContext

from .transform import bare

PREDICATES = frozenset(
    {
        "real",
        "integer",
        "positive",
        "negative",
        "nonzero",
        "nonnegative",
        "nonpositive",
        "finite",
        "complex",
        "rational",
        "zero",
        "even",
        "odd",
    }
)


@dataclass(frozen=True)
class NativePremises:
    """Compiled only on native demand; unsupported inputs retain their authored bytes."""

    context: Any
    symbols: dict[str, Any] = field(default_factory=dict, init=False, repr=False)

    @cached_property
    def records(self):
        value = json.loads(self.context.assumptions)
        return tuple(value) if isinstance(value, list) else (value,)

    @cached_property
    def unsupported(self) -> tuple[Any, ...]:
        return tuple(
            record
            for record in self.records
            if not (
                isinstance(record, dict)
                and set(record) <= {"symbol", "predicate", "value"}
                and isinstance(record.get("symbol"), str)
                and record.get("predicate") in PREDICATES
                and isinstance(record.get("value", True), bool)
            )
        )

    def symbol(self, name: str):
        name = bare(name)
        if name not in self.symbols:
            declarations = [d for d in self.context.declarations if bare(d.symbol) == name]
            # Scope identity is semantic, not an incidental task/process address. Source
            # declarations distinguish same-spelling entities; no variable is implicitly real.
            scoped = [d for d in declarations if d.scope is not None]
            if scoped:
                basis = json.dumps(sorted((d.source_id, d.scope, d.evidence) for d in scoped))
                index = int(hashlib.sha256(basis.encode()).hexdigest()[:30], 16)
                self.symbols[name] = sympy.Dummy(name, dummy_index=index)
            else:
                self.symbols[name] = sympy.Symbol(name)
        return self.symbols[name]

    @cached_property
    def predicate(self):
        facts = []
        for record in self.records:
            if record in self.unsupported:
                continue
            fact = getattr(sympy.Q, record["predicate"])(self.symbol(record["symbol"]))
            facts.append(fact if record.get("value", True) else ~fact)
        return sympy.And(*facts)

    def ask(self, proposition):
        return sympy.ask(proposition, self.predicate, context=AssumptionsContext())

    def validate(self) -> None:
        # ask validates consistency even if the proposition itself is trivially true.
        self.ask(sympy.Q.real(sympy.Integer(0)))

    def refine(self, expression):
        """Run native 1.14 refine with an isolated ask binding.

        refine has no context parameter. Its native handlers share module globals and
        call ask without one. Copy their function namespace, binding ask to an empty
        native AssumptionsContext; never alter SymPy's module or global assumptions.
        """
        native = importlib.import_module("sympy.assumptions.refine")
        namespace = dict(vars(native))
        namespace["ask"] = lambda proposition, assumptions=True: sympy.ask(
            proposition, assumptions, context=AssumptionsContext()
        )
        for name, function in vars(native).items():
            if isinstance(function, FunctionType) and function.__module__ == native.__name__:
                clone = FunctionType(
                    function.__code__, namespace, name, function.__defaults__, function.__closure__
                )
                clone.__kwdefaults__ = function.__kwdefaults__
                namespace[name] = clone
        handlers = {}
        for name, handler in native.handlers_dict.items():
            if handler.__module__ == native.__name__:
                handlers[name] = namespace[handler.__name__]
            else:
                # Native matrix handlers live in their expression modules. Give
                # those functions the same isolated ask boundary as scalar handlers.
                external = {
                    **handler.__globals__,
                    "ask": namespace["ask"],
                    "refine": namespace["refine"],
                }
                handlers[name] = FunctionType(
                    handler.__code__,
                    external,
                    handler.__name__,
                    handler.__defaults__,
                    handler.__closure__,
                )
        namespace["handlers_dict"] = handlers
        return namespace["refine"](expression, self.predicate)

    def native_symbols(self, names):
        return MappingProxyType({name: self.symbol(name) for name in names})
