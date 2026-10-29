"""Pydantic applicability probe for prepared-release adapters, dumps and shared-$defs schemas.

Pure Python, no database. Uses the repository's real release compiler on a small LinkML schema
so field annotations, MISSING defaults, aliases and the conditional-rule JSON Schema hook are the
compiler's own. Prints one line per check: `<id> <observation>`.
"""

from __future__ import annotations

import json
import math
from decimal import Decimal
from typing import Any, get_args, get_origin

import pydantic
import pydantic_core
import yaml
from pydantic import BaseModel, ConfigDict, PostgresDsn, TypeAdapter, ValidationError
from pydantic.json_schema import models_json_schema

from corpus_structure.semantic import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
    prepare_release,
)
from corpus_structure.semantic.composed import composed_dependencies

print("versions", pydantic.VERSION, pydantic_core.__version__)

SCHEMA: dict[str, Any] = {
    "id": "https://example.org/probe",
    "name": "probe",
    "prefixes": {"ex": "https://example.org/", "xsd": "http://www.w3.org/2001/XMLSchema#"},
    "default_prefix": "ex",
    "types": {
        "string": {"base": "str", "uri": "xsd:string"},
        "decimal": {"base": "Decimal", "uri": "xsd:decimal"},
        "float": {"base": "float", "uri": "xsd:float"},
        "integer": {"base": "int", "uri": "xsd:integer"},
    },
    "classes": {
        "Thing": {
            "attributes": {
                "id": {"identifier": True},
                "status": {"range": "string"},
                "label": {"range": "string"},
                "reason": {"range": "string"},
            },
            "rules": [
                {
                    "preconditions": {"slot_conditions": {"status": {"equals_string": "ready"}}},
                    "postconditions": {"slot_conditions": {"label": {"required": True}}},
                    "elseconditions": {"slot_conditions": {"reason": {"required": True}}},
                }
            ],
        },
        "Holder": {
            "attributes": {
                "id": {"identifier": True},
                "score": {"range": "float"},
                "amount": {"range": "decimal", "minimum_value": 0},
                "tags": {"range": "string", "multivalued": True},
                "scores": {"range": "float", "multivalued": True},
                "thing": {"range": "Thing", "inlined": True},
                "things": {"range": "Thing", "multivalued": True, "inlined": True},
                "listed": {
                    "range": "Thing",
                    "multivalued": True,
                    "inlined": True,
                    "inlined_as_list": True,
                },
                "ref": {"range": "Thing"},
                "renamed": {"range": "string", "alias": "renamed_external"},
            }
        },
    },
}

release = prepare_release(
    SourceBundle("probe", (SourceArtifact("probe", yaml.safe_dump(SCHEMA).encode()),)),
    composed_dependencies(ResolvedDependencies()),
    profile=PreparationProfile(version="semantic-2"),
)
adapters = dict(release._adapters)
models = {name: adapter._type for name, adapter in adapters.items()}  # probe-only private read
Holder, Thing = models["Holder"], models["Thing"]


def check(label: str, fn) -> None:
    try:
        print(label, fn())
    except Exception as exc:  # noqa: BLE001 - probe reports every outcome
        print(label, f"raised {type(exc).__name__}: {str(exc).splitlines()[0][:160]}")


# P1 -- per-property adapters: config propagation, annotation resolution, public route.
for name in ("score", "scores", "thing", "things", "listed", "ref", "amount"):
    print("P1-annotation", name, repr(Holder.model_fields[name].annotation)[:160])

nan = float("nan")
check("P1a model refuses NaN score", lambda: Holder.model_validate({"id": "h", "score": nan}))
check(
    "P1b property_adapter(score) accepts NaN strict",
    lambda: release.property_adapter("Holder", "score").validate_python(nan, strict=True),
)
check(
    "P1c property_adapter(scores,item) accepts inf strict",
    lambda: release.property_adapter("Holder", "scores", item=True).validate_python(
        math.inf, strict=True
    ),
)
CONFIG = ConfigDict(strict=True, allow_inf_nan=False)


def public_adapter(model: type[BaseModel], field: str, *, item: bool = False) -> TypeAdapter:
    """Candidate public route: model class kept at preparation; config only where allowed."""
    info = model.model_fields[field]
    annotation = info.rebuild_annotation()
    if item:
        base = info.annotation
        annotation = get_args(base)[-1 if get_origin(base) is dict else 0]
    try:
        return TypeAdapter(annotation, config=CONFIG)
    except pydantic.PydanticUserError as exc:
        if exc.code != "type-adapter-config-unused":
            raise
        return TypeAdapter(annotation)  # a model carries its own config


check(
    "P1d public adapter(score) refuses NaN",
    lambda: public_adapter(Holder, "score").validate_python(nan),
)
check(
    "P1e public adapter(scores,item) refuses inf",
    lambda: public_adapter(Holder, "scores", item=True).validate_python(math.inf),
)
check(
    "P1f public adapter(thing) config route",
    lambda: type(public_adapter(Holder, "thing").validate_python({"id": "t", "reason": "r"})),
)
check(
    "P1g TypeAdapter(Thing, config=...) refused",
    lambda: TypeAdapter(Thing, config=CONFIG),
)
check(
    "P1h TypeAdapter(tuple[Thing,...], config=...) allowed",
    lambda: TypeAdapter(tuple[Thing, ...], config=CONFIG).validate_python(
        ({"id": "t", "reason": "r"},)
    ),
)
check(
    "P1i public adapter(amount) keeps ge=0",
    lambda: public_adapter(Holder, "amount").validate_python(Decimal("-1")),
)
check(
    "P1j public adapter(amount) strict refuses str",
    lambda: public_adapter(Holder, "amount").validate_python("1"),
)
check(
    "P1k strict per-call == strict config for amount",
    lambda: release.property_adapter("Holder", "amount").validate_python("1", strict=True),
)
check(
    "P1l public adapter(things,item) keyed member type",
    lambda: type(
        public_adapter(Holder, "things", item=True).validate_python({"id": "t", "reason": "r"})
    ),
)
check(
    "P1m whole-field adapter(things) keeps keyed validator",
    lambda: public_adapter(Holder, "things").validate_python(
        {"wrong": {"id": "t", "reason": "r"}}
    ),
)
check("P1n public attribute for adapter type?", lambda: [a for a in dir(adapters["Holder"]) if "type" in a.lower()])

# P2 -- model_dump / dump_python(exclude_unset=True) versus the hand projections.
from corpus_structure.semantic.consolidation import plain  # noqa: E402
from corpus_structure.semantic.domain_operations import _native, _plain  # noqa: E402

value = adapters["Holder"].validate_python(
    {
        "id": "h",
        "amount": Decimal("1.50"),
        "tags": ("a", "b"),
        "thing": {"id": "t1", "status": "ready", "label": "L"},
        "things": {"t2": {"id": "t2", "reason": "r"}},
        "listed": ({"id": "t3", "reason": "r"},),
        "ref": "t9",
        "renamed_external": "x",
    },
    strict=True,
)
dumped = value.model_dump(exclude_unset=True)
print("P2a model_dump(exclude_unset)", dumped)
print("P2b _plain", _plain(value))
print("P2c _native", _native(value))
print("P2d consolidation.plain == _plain", plain(value) == _plain(value))


def lists(obj: Any) -> Any:
    if isinstance(obj, (list, tuple)):
        return [lists(v) for v in obj]
    if isinstance(obj, dict):
        return {k: lists(v) for k, v in obj.items()}
    return obj


print("P2e dump == _native (tuple-preserving)", dumped == _native(value))
print("P2f lists(dump) == _plain", lists(dumped) == _plain(value))
print("P2g dump keys are field names (renamed)", "renamed" in dumped, "renamed_external" in dumped)
print("P2h dump by_alias keys", sorted(value.model_dump(exclude_unset=True, by_alias=True)))
item_adapter = release.property_adapter("Holder", "listed")
item_value = item_adapter.validate_python(({"id": "t3", "reason": "r"},), strict=True)
print(
    "P2i TypeAdapter.dump_python(exclude_unset) on adapter output == _native",
    item_adapter.dump_python(item_value, exclude_unset=True) == _native(item_value),
)
explicit = adapters["Thing"].validate_python({"id": "t", "reason": "r", "label": "x"})
print("P2j explicit-set fields kept", explicit.model_dump(exclude_unset=True))

# P3 -- one shared-$defs document versus per-class artifacts; conditional hook placement.
per_class = {name: adapter.json_schema() for name, adapter in adapters.items()}
print("P3a per-class Thing top-level has if/then", "if" in per_class["Thing"], "then" in per_class["Thing"])
holder_defs = per_class["Holder"].get("$defs", {})
print("P3b per-class Holder $defs keys", sorted(holder_defs))
print("P3c Holder $defs.Thing carries if/then", "if" in holder_defs.get("Thing", {}))
thing_prop = per_class["Holder"]["properties"]["thing"]
print("P3d Holder.properties.thing", json.dumps(thing_prop, sort_keys=True)[:200])
keys_map, shared = models_json_schema([(models[n], "validation") for n in sorted(models)])
print("P3e models_json_schema map", {k[0].__name__: v for k, v in keys_map.items()})
print("P3f shared $defs keys", sorted(shared.get("$defs", {})))
print("P3g shared $defs.Thing carries if/then", "if" in shared["$defs"]["Thing"])
print(
    "P3h shared Thing def == per-class Thing (minus title/$defs)",
    {k: v for k, v in shared["$defs"]["Thing"].items()}
    == {k: v for k, v in per_class["Thing"].items() if k != "$defs"},
)
ta_map, ta_shared = TypeAdapter.json_schemas(
    [(n, "validation", adapters[n]) for n in sorted(adapters)]
)
print("P3i TypeAdapter.json_schemas == models_json_schema defs", ta_shared == shared)
print(
    "P3j shared Holder def == per-class Holder (minus $defs)",
    shared["$defs"]["Holder"] == {k: v for k, v in per_class["Holder"].items() if k != "$defs"},
)

# P4 -- PostgresDsn and a socket-only libpq URL.
check(
    "P4a PostgresDsn socket-only URL",
    lambda: TypeAdapter(PostgresDsn).validate_python(
        "postgresql:///corpus?host=/var/run/postgresql&port=5434"
    ),
)
check(
    "P4b PostgresDsn host URL",
    lambda: str(TypeAdapter(PostgresDsn).validate_python("postgresql://reader@localhost:5434/corpus")),
)
_ = ValidationError  # imported for readers; failures print above
