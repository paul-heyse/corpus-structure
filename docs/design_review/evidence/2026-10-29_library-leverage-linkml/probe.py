"""Pure-Python probes of linkml-runtime 1.12.1 and curies 0.15.5 semantics.

No database, network service or filesystem schema is used; every schema is an in-memory dict.
Run from the repository root: uv run --no-sync python <this file>
"""

from __future__ import annotations

import copy
import json
from importlib.metadata import version

import linkml_runtime.utils.schemaview as sv_module
from curies import Converter
from linkml_runtime.dumpers import json_dumper
from linkml_runtime.linkml_model.meta import SchemaDefinition
from linkml_runtime.loaders import yaml_loader
from linkml_runtime.processing.referencevalidator import ReferenceValidator
from linkml_runtime.utils.schemaview import SchemaView

print("versions:", {n: version(n) for n in ("linkml", "linkml-runtime", "curies", "pyoxigraph")})

TYPES = {
    "string": {"base": "str", "uri": "xsd:string"},
    "integer": {"base": "int", "uri": "xsd:integer"},
}


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def attempt(label: str, fn) -> None:
    try:
        print(f"{label}: {fn()!r}")
    except Exception as exc:  # report, never hide
        print(f"{label}: RAISED {type(exc).__name__}: {str(exc)[:200]}")


# ---------------------------------------------------------------- P1 importmap composition
section("P1 importmap: in-memory composition, fallback and duplicates")
fallback_calls: list[str] = []
_real_wrap = sv_module.load_schema_wrap


def _spy_wrap(path, **kwargs):
    fallback_calls.append(str(path))
    raise FileNotFoundError(f"probe blocked filesystem/network load of {path}")


sv_module.load_schema_wrap = _spy_wrap

mod_a = {
    "id": "https://example.org/a",
    "name": "mod_a",
    "default_prefix": "a",
    "prefixes": {"a": "https://example.org/a/"},
    "types": TYPES,
    "classes": {"Thing": {"attributes": {"label": {"range": "string"}}}},
}
mod_b = {
    "id": "https://example.org/b",
    "name": "mod_b",
    "default_prefix": "b",
    "prefixes": {"b": "https://example.org/b/"},
    "classes": {"Other": {"is_a": "Thing"}, "Thing": {"description": "duplicate in b"}},
}
root = {
    "id": "https://example.org/root",
    "name": "root",
    "default_prefix": "r",
    "prefixes": {"r": "https://example.org/root/"},
    "imports": ["mod_a", "https://example.org/b"],
}
importmap = {"mod_a": copy.deepcopy(mod_a), "https://example.org/b": copy.deepcopy(mod_b)}
pristine = copy.deepcopy(importmap)
view = SchemaView(yaml_loader.load(copy.deepcopy(root), SchemaDefinition), importmap=importmap)
attempt("imports_closure", lambda: view.imports_closure())
attempt("filesystem/network fallback calls", lambda: list(fallback_calls))
attempt("importmap dicts unchanged by loading", lambda: importmap == pristine)
attempt(
    "duplicate class Thing: winner description (no refusal)",
    lambda: view.get_class("Thing").description,
)
attempt("Other class_uri via get_uri (unmerged)", lambda: view.get_uri("Other", expand=True))
attempt("Thing from_schema", lambda: view.get_class("Thing").from_schema)
merged_view = SchemaView(yaml_loader.load(copy.deepcopy(root), SchemaDefinition), importmap=importmap)
merged_view.merge_imports()
merged = copy.deepcopy(merged_view.schema)
attempt("after merge: Thing kept from", lambda: merged.classes["Thing"].description)
fresh = SchemaView(merged)
attempt("after merge + new view: get_uri('Other')", lambda: fresh.get_uri("Other", expand=True))

fallback_calls.clear()
missing_root = {**root, "imports": ["mod_a", "not_supplied"]}
v_missing = SchemaView(yaml_loader.load(copy.deepcopy(missing_root), SchemaDefinition), importmap=importmap)
attempt("missing import closure", lambda: v_missing.imports_closure())
attempt("missing import fallback calls", lambda: list(fallback_calls))

fallback_calls.clear()
types_root = {**root, "imports": ["linkml:types"]}
v_types = SchemaView(yaml_loader.load(copy.deepcopy(types_root), SchemaDefinition), importmap={})
attempt("linkml:types closure with empty importmap", lambda: v_types.imports_closure())
attempt("linkml:types fallback calls (installed metamodel path)", lambda: list(fallback_calls))
sv_module.load_schema_wrap = _real_wrap

# ---------------------------------------------------------------- P2 ReferenceValidator
section("P2 ReferenceValidator: dangling and duplicate references")
ref_schema = {
    "id": "https://example.org/ref",
    "name": "ref",
    "default_prefix": "ref",
    "prefixes": {"ref": "https://example.org/ref/"},
    "default_range": "string",
    "types": TYPES,
    "classes": {
        "Item": {"attributes": {"id": {"identifier": True}, "label": {}}},
        "Container": {
            "tree_root": True,
            "attributes": {
                "items": {
                    "range": "Item",
                    "multivalued": True,
                    "inlined": True,
                    "inlined_as_list": True,
                },
                "refs": {"range": "Item", "multivalued": True, "inlined": False},
            },
        },
    },
}
rv = ReferenceValidator(SchemaView(yaml_loader.load(copy.deepcopy(ref_schema), SchemaDefinition)))
instance = {
    "items": [{"id": "ref:a", "label": "A"}, {"id": "ref:a", "label": "A again"}],
    "refs": ["ref:a", "ref:missing"],
}
report = rv.validate(copy.deepcopy(instance), "Container")
attempt("results for dangling ref:missing + duplicate id ref:a", lambda: [
    (str(r.type), r.subject, r.info) for r in report.results
])

# ---------------------------------------------------------------- P3 type semantics
section("P3 type_ancestors / induced_type / materialize_derived_schema vs conjunction")
type_schema = {
    "id": "https://example.org/t",
    "name": "t",
    "default_prefix": "t",
    "prefixes": {"t": "https://example.org/t/"},
    "types": {
        **TYPES,
        "Code": {"typeof": "string", "pattern": "^[A-Z]"},
        "ShortCode": {"typeof": "Code", "pattern": "^.{1,3}$"},
        "Pos": {"typeof": "integer", "minimum_value": 0},
        "Small": {"typeof": "Pos", "maximum_value": 10},
        "Looser": {"typeof": "Small", "minimum_value": -5},
    },
    "classes": {
        "Holder": {
            "attributes": {
                "code": {"range": "ShortCode", "pattern": "^S"},
                "n": {"range": "Looser", "maximum_value": 20},
            }
        }
    },
}
tview = SchemaView(yaml_loader.load(copy.deepcopy(type_schema), SchemaDefinition))
attempt("type_ancestors(ShortCode)", lambda: tview.type_ancestors("ShortCode"))
attempt("type_ancestors(Looser)", lambda: tview.type_ancestors("Looser"))
attempt("induced_type(ShortCode).pattern", lambda: tview.induced_type("ShortCode").pattern)
attempt(
    "induced_type(Looser) min/max",
    lambda: (tview.induced_type("Looser").minimum_value, tview.induced_type("Looser").maximum_value),
)
attempt(
    "induced_slot(n, Holder) min/max",
    lambda: (tview.induced_slot("n", "Holder").minimum_value, tview.induced_slot("n", "Holder").maximum_value),
)
attempt("induced_slot(code, Holder).pattern", lambda: tview.induced_slot("code", "Holder").pattern)
before = json_dumper.dumps(tview.schema)
derived = tview.materialize_derived_schema()
attempt("derived type Looser min/max", lambda: (derived.types["Looser"].minimum_value, derived.types["Looser"].maximum_value))
attempt("derived type ShortCode pattern", lambda: derived.types["ShortCode"].pattern)
attempt(
    "derived Holder.n min/max",
    lambda: (derived.classes["Holder"].attributes["n"].minimum_value, derived.classes["Holder"].attributes["n"].maximum_value),
)
attempt("derived Holder.code pattern", lambda: derived.classes["Holder"].attributes["code"].pattern)
attempt("materialize_derived_schema left source unchanged", lambda: json_dumper.dumps(tview.schema) == before)
undeclared = copy.deepcopy(type_schema)
undeclared["types"].pop("string")
uview = SchemaView(yaml_loader.load(undeclared, SchemaDefinition))
attempt("type_ancestors(ShortCode) with undeclared 'string'", lambda: uview.type_ancestors("ShortCode"))

# ---------------------------------------------------------------- P4 induction mutation
section("P4 induction mutates asserted schema (domain_of)")
shared = {
    "id": "https://example.org/m",
    "name": "m",
    "default_prefix": "m",
    "prefixes": {"m": "https://example.org/m/"},
    "default_range": "string",
    "types": TYPES,
    "slots": {"name": {}},
    "classes": {"A": {"slots": ["name"]}, "B": {"slots": ["name"]}},
}
mschema = yaml_loader.load(copy.deepcopy(shared), SchemaDefinition)
mview = SchemaView(mschema)
attempt("asserted domain_of before induction", lambda: list(mschema.slots["name"].domain_of))
mview.class_induced_slots("A")
attempt("asserted domain_of after class_induced_slots(A)", lambda: list(mschema.slots["name"].domain_of))
mschema2 = yaml_loader.load(copy.deepcopy(shared), SchemaDefinition)
snapshot = json_dumper.dumps(mschema2)
from linkml.generators.jsonschemagen import JsonSchemaGenerator  # noqa: E402

JsonSchemaGenerator(mschema2).serialize()
attempt("schema handed to JsonSchemaGenerator unchanged", lambda: json_dumper.dumps(mschema2) == snapshot)
attempt("domain_of after generator", lambda: list(mschema2.slots["name"].domain_of))
attempt("metamodel_version after generator", lambda: mschema2.metamodel_version)

# ---------------------------------------------------------------- P5 structured annotations
section("P5 structured (nested) annotation values")
for label, annotations in {
    "list value": {"ph:foreign_keys": [{"columns": ["a"], "target": "t.c"}]},
    "explicit value wrapper with mapping": {"ph:check": {"value": {"name": "c1", "sql": "a > 0"}}},
    "bare mapping value": {"ph:check": {"name": "c1", "sql": "a > 0"}},
    "nested annotations": {"ph:index": {"value": "ix_a", "annotations": {"ph:unique": True}}},
}.items():
    doc = {
        "id": "https://example.org/p",
        "name": "p",
        "default_prefix": "p",
        "prefixes": {"p": "https://example.org/p/", "ph": "https://example.org/ph/"},
        "types": TYPES,
        "classes": {"T": {"annotations": annotations, "attributes": {"a": {"range": "integer"}}}},
    }

    stage = {"name": "yaml_loader.load"}

    def load(doc=doc, stage=stage):
        schema = yaml_loader.load(copy.deepcopy(doc), SchemaDefinition)
        stage["name"] = "SchemaView.get_class"
        view = SchemaView(schema)
        out = {}
        for tag, ann in view.get_class("T").annotations.items():
            stage["name"] = "read value"
            value = ann.value
            out[str(tag)] = (type(value).__name__, value if isinstance(value, (str, int, bool)) else repr(value)[:120])
            if ann.annotations:
                out[str(tag) + "/nested"] = {str(k): v.value for k, v in ann.annotations.items()}
        stage["name"] = "json_dumper.dumps(schema)"
        out["round_trip_class_annotations"] = json.loads(json_dumper.dumps(schema))["classes"]["T"]["annotations"]
        return out

    attempt(label, load)
    print(f"  (last stage reached: {stage['name']})")

# ---------------------------------------------------------------- P6 curies parity
section("P6 curies Converter vs archived-prefix expansion/compaction")
prefixes = {
    "ex": "https://example.org/",
    "exs": "https://example.org/sub/",
    "ns": "https://ns.org/x#",
}


def project_expand(name: str) -> str:  # transcribed from the inspected expansion contract
    if name.startswith(("http://", "https://", "urn:")):
        return name
    prefix, separator, local = name.partition(":")
    if separator and prefix in prefixes:
        return prefixes[prefix] + local
    raise KeyError(name)


def project_compact(iri: str) -> str:
    choices = [(len(u), p + ":" + iri[len(u):]) for p, u in prefixes.items() if iri.startswith(u)]
    return max(choices)[1] if choices else iri


conv = Converter.from_prefix_map(prefixes)
for name in ("ex:a", "exs:b", "ex:sub/b", "ns:frag", "ex:", "missing:a", "nocolon", "https://other.org/z", "urn:x:y", "file:/tmp/x"):
    attempt(f"expand {name!r} project", lambda name=name: project_expand(name))
    attempt(f"expand {name!r} curies.expand(strict)", lambda name=name: conv.expand(name, strict=True))
    attempt(f"expand {name!r} curies.expand_or_standardize(strict)", lambda name=name: conv.expand_or_standardize(name, strict=True))
for iri in ("https://example.org/sub/b", "https://example.org/a", "https://example.org/", "https://ns.org/x#frag", "https://unknown.org/q"):
    attempt(f"compact {iri!r} project", lambda iri=iri: project_compact(iri))
    attempt(f"compact {iri!r} curies.compress(passthrough)", lambda iri=iri: conv.compress(iri, passthrough=True))
dupes = {"d1": "https://dup.org/", "d2": "https://dup.org/"}
attempt("duplicate URI prefixes strict", lambda: Converter.from_prefix_map(dupes))
attempt("duplicate URI prefixes non-strict compress", lambda: Converter.from_prefix_map(dupes, strict=False).compress("https://dup.org/z"))
attempt("project tie-break for same", lambda: max((len(u), p + ":z") for p, u in dupes.items()))
