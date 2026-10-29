"""rule-engine 5.1.0: which model shapes map to rule types, and is there a non-underscore route to
the resolved OBJECT owner of an attribute access?

Pure Python; no database. Pydantic models are built with `create_model` and the same annotation
shapes a release-generated model uses (Annotated+Field, tuple[T, ...], dict[str, T], Literal for
`equals_string`, a str enum, a discriminated union of concrete classes, optional).
"""

from __future__ import annotations

import dataclasses
import enum
import json
from typing import Annotated, Literal

import pydantic
import rule_engine
from pydantic import BaseModel, Field, create_model
from rule_engine import Context, DataType, Rule
from rule_engine.ast import GetAttributeExpression

OUT: dict[str, object] = {"rule_engine": rule_engine.__version__, "pydantic": pydantic.VERSION}


class Kind(enum.StrEnum):
    A = "a"
    B = "b"


class Q(BaseModel):
    kind: Literal["q"] = "q"
    x: str


class R(BaseModel):
    kind: Literal["r"] = "r"
    y: int


SHAPES = {
    "str": str,
    "Annotated[str, Field(pattern)]": Annotated[str, Field(pattern="^a")],
    "tuple[str, ...]": tuple[str, ...],
    "list[str]": list[str],
    "dict[str, int]": dict[str, int],
    "str | None": str | None,
    "Literal['x']": Literal["x"],
    "StrEnum": Kind,
    "Q | R (discriminated)": Annotated[Q | R, Field(discriminator="kind")],
    "BaseModel Q": Q,
}

mapped: dict[str, str] = {}
for label, annotation in SHAPES.items():
    try:
        mapped[label] = repr(DataType.from_type(annotation))
    except Exception as error:
        mapped[label] = f"{type(error).__name__}: {error}"
OUT["DataType.from_type"] = mapped

Generated = create_model(
    "Generated",
    __config__=pydantic.ConfigDict(frozen=True, extra="forbid", strict=True),
    name=(str, ...),
    tags=(tuple[str, ...], ()),
    kind=(Kind, Kind.A),
)
try:
    rule_engine.type_resolver_from_dataclass(Generated)
    OUT["type_resolver_from_dataclass(BaseModel)"] = "accepted"
except Exception as error:
    OUT["type_resolver_from_dataclass(BaseModel)"] = f"{type(error).__name__}: {error}"


@pydantic.dataclasses.dataclass(frozen=True)
class PdView:
    name: str
    tags: tuple[str, ...]
    kind: Kind
    note: str | None = None


for strict in (True, False):
    try:
        resolver = rule_engine.type_resolver_from_dataclass(PdView, strict=strict)
        OUT[f"pydantic dataclass strict={strict}"] = {
            n: repr(resolver(n)) for n in ("name", "tags", "kind", "note")
        }
    except Exception as error:
        OUT[f"pydantic dataclass strict={strict}"] = f"{type(error).__name__}: {error}"
OUT["pydantic dataclass is_dataclass"] = dataclasses.is_dataclass(PdView)

# The owner of an attribute access: private `_object_type` versus `object.result_type`.
Entity = DataType.OBJECT("Entity", attributes={"type": DataType.STRING}, accessor=getattr)
Claim = DataType.OBJECT(
    "Claim",
    attributes={"subject": Entity, "object": DataType.NULLABLE(Entity), "predicate": DataType.STRING},
    accessor=getattr,
)
ctx = Context(type_resolver=rule_engine.type_resolver_from_dict({"claim": Claim}),
              mapping_attribute_lookup=False)
rows = []
for text in ('claim.subject.type == "x"', 'claim.object&.type == "x"', '[e.type for e in [claim.subject]][0] == "x"'):
    rule = Rule(text, context=ctx)
    stack = [rule.statement.expression]
    while stack:
        node = stack.pop()
        if isinstance(node, GetAttributeExpression):
            public = DataType.NULLABLE.unwrap(node.object.result_type)
            rows.append({
                "rule": text,
                "attribute": node.name,
                "_object_type": getattr(node._object_type, "name", None),
                "object.result_type (unwrapped)": getattr(public, "name", repr(public)),
                "agree": getattr(node._object_type, "name", None) == getattr(public, "name", None),
            })
        for name in ("left", "right", "object", "container", "member", "item", "result", "iterable", "condition"):
            child = getattr(node, name, None)
            if child is not None and hasattr(child, "result_type"):
                stack.append(child)
OUT["owner routes"] = rows

if __name__ == "__main__":
    print(json.dumps(OUT, indent=2, default=str))
