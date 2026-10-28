"""Q-1 (P0-M-Q1): can a PydanticGenerator subclass over S4's core.yaml produce the core shapes?

    UV_PROJECT_ENVIRONMENT=$PWD/build/probe-venv uv run --project \
        docs/design_review/evidence/2026-10-28_phase0-model-probes \
        python docs/design_review/evidence/2026-10-28_phase0-model-probes/code/q1_stage_b.py

Runs code/q1_build.py (patch S4's core.yaml, lint, generate results/q1/generated/core_shapes.py), then
compares the generated module with the hand shapes in python/corpus-structure/src/corpus_structure/core/
values.py and batch.py (read-only import):
1. the feature checks the question names;
2. structure: per class, fields (normalized annotation, default, alias, exclude_if, order), config,
   bases and validators; the four union aliases;
3. JSON Schemas: the generated adapters rendered with the product's CoreJsonSchema against the
   committed core/schemas/*.json, byte for byte, then without descriptions, then order-insensitive;
4. S4's 135 batches (as written and after S4's recorded V1/V2 canonicalization), validated by the hand
   and the generated models: verdicts, error (loc, type) lists and, for valid batches, the dumps;
5. seeded errors on one valid authored batch.
Outputs under results/q1/.
"""

from __future__ import annotations

import copy
import importlib
import json
import re
import subprocess
import sys
import typing
from pathlib import Path

from pydantic import BaseModel, TypeAdapter, ValidationError

HERE = Path(__file__).resolve().parent
FOLDER = HERE.parent
REPO = FOLDER.parents[3]
OUT = FOLDER / "results/q1"
PRODUCT = REPO / "python/corpus-structure/src"
SPIKES = REPO / "docs/design_review/evidence/2026-10-28_design-spikes/code"
COMMITTED = PRODUCT / "corpus_structure/core/schemas"

sys.path[:0] = [str(OUT / "generated"), str(HERE / "q1"), str(PRODUCT), str(SPIKES)]

FORM_FILES = ["value.authored", "value.stored", "condition.authored", "condition.stored",
              "batch.authored", "batch.stored"]


def load():
    subprocess.run([sys.executable, str(HERE / "q1_build.py")], check=True)
    from corpus_structure.core import batch as hb
    from corpus_structure.core import values as hv
    gen = importlib.import_module("core_shapes")
    return hv, hb, gen


# ---------------------------------------------------------------------------------------------
# 1. features
# ---------------------------------------------------------------------------------------------
def features(gen) -> dict:
    from pydantic import MISSING

    out = {}
    cond = TypeAdapter(gen.AuthoredCondition).json_schema()
    out["named_recursive_condition"] = ("AuthoredCondition" in cond.get("$defs", {}) and
                                        cond.get("$ref") == "#/$defs/AuthoredCondition")
    out["op_discriminator"] = "discriminator" in cond["$defs"]["AuthoredCondition"]
    val = TypeAdapter(gen.StoredValue).json_schema()
    out["t_discriminator"] = val.get("discriminator", {}).get("propertyName") == "t"
    f = gen.NumberValue.model_fields["unit"]
    out["missing_default"] = f.default is MISSING
    out["missing_dumped_absent"] = "unit" not in gen.NumberValue(t="number", v="1").model_dump()
    out["frozen"] = gen.AuthoredBatch.model_config.get("frozen") is True
    out["extra_forbid"] = gen.AuthoredBatch.model_config.get("extra") == "forbid"
    out["tuples"] = typing.get_origin(gen.AuthoredBatch.model_fields["claims"].annotation) is tuple
    out["form_variants"] = all(hasattr(gen, n) for n in ("AuthoredPhrase", "StoredPhrase", "AuthoredBatch", "StoredBatch"))
    out["stored_only_fields"] = ("start" in gen.StoredPhrase.model_fields and "start" not in gen.AuthoredPhrase.model_fields)
    out["prefixed_aliases"] = gen.StoredQualifiers.model_fields["modality"].alias == "core:modality"
    out["default_excluded"] = gen.StoredQualifiers().model_dump() == {}
    return out


# ---------------------------------------------------------------------------------------------
# 2. structure
# ---------------------------------------------------------------------------------------------
_QUAL = re.compile(r"\b(?:[a-z_][a-z0-9_]*\.)+([A-Za-z_][A-Za-z0-9_]*)")


def norm(t: object) -> str:
    s = repr(t)
    s = _QUAL.sub(r"\1", s)
    s = s.replace("typing.", "").replace("<class '", "").replace("'>", "")
    return s


def classes_of(mod, names=None) -> dict[str, type]:
    out = {}
    for k, v in vars(mod).items():
        if isinstance(v, type) and issubclass(v, BaseModel) and v.__module__ == mod.__name__ and k != "CoreModel" \
                and v.__name__ == k:
            out[k] = v
    return out


def field_view(info) -> dict:
    from pydantic import MISSING

    if info.default_factory is not None:
        default = f"factory:{getattr(info.default_factory, '__name__', info.default_factory)}"
    elif info.default is MISSING:
        default = "MISSING"
    elif info.is_required():
        default = "required"
    else:
        default = repr(info.default)
    return {"annotation": norm(info.annotation), "default": default, "alias": info.alias,
            "exclude_if": info.exclude_if is not None, "metadata": sorted(norm(m) for m in info.metadata),
            "discriminator": info.discriminator if isinstance(info.discriminator, str) else norm(info.discriminator)}


CONFIG_KEYS = ("frozen", "extra", "validate_by_alias", "validate_by_name", "serialize_by_alias")


def class_view(c: type[BaseModel]) -> dict:
    dec = c.__pydantic_decorators__
    return {
        "bases": [b.__name__ for b in c.__bases__],
        "config": {k: c.model_config.get(k) for k in CONFIG_KEYS if c.model_config.get(k) is not None},
        "fields": {n: field_view(i) for n, i in c.model_fields.items()},
        "order": list(c.model_fields),
        "model_validators": len(dec.model_validators),
        "field_validators": len(dec.field_validators),
    }


def structure(hv, hb, gen) -> dict:
    hand = {**classes_of(hv), **classes_of(hb)}
    genc = classes_of(gen)
    rows, missing, extra = [], sorted(set(hand) - set(genc)), sorted(set(genc) - set(hand))
    for name in sorted(set(hand) & set(genc)):
        a, b = class_view(hand[name]), class_view(genc[name])
        diffs = []
        for k in ("bases", "config", "order", "model_validators", "field_validators"):
            if a[k] != b[k]:
                diffs.append({"what": k, "hand": a[k], "generated": b[k]})
        for f in sorted(set(a["fields"]) | set(b["fields"])):
            fa, fb = a["fields"].get(f), b["fields"].get(f)
            if fa != fb:
                if fa is None or fb is None:
                    diffs.append({"what": f"field {f}", "hand": fa, "generated": fb})
                else:
                    for k in fa:
                        if fa[k] != fb[k]:
                            diffs.append({"what": f"field {f}.{k}", "hand": fa[k], "generated": fb[k]})
        rows.append({"class": name, "equal": not diffs, "diffs": diffs})
    aliases = {}
    for n in ("AuthoredValue", "StoredValue", "AuthoredCondition", "StoredCondition"):
        ha, ga = getattr(hv, n).__value__, getattr(gen, n).__value__
        aliases[n] = {"equal": norm(ha) == norm(ga), "hand": norm(ha), "generated": norm(ga)}
    return {"compared": len(rows), "equal": sum(r["equal"] for r in rows), "classes": rows,
            "hand_only": missing, "generated_only": extra, "aliases": aliases}


# ---------------------------------------------------------------------------------------------
# 3. JSON Schemas
# ---------------------------------------------------------------------------------------------
def strip(node, key="description"):
    if isinstance(node, dict):
        return {k: strip(v, key) for k, v in node.items() if k != key}
    if isinstance(node, list):
        return [strip(v, key) for v in node]
    return node


def canon(node):
    return json.dumps(node, sort_keys=True)


def json_paths_diff(a, b, path="$", out=None, limit=40):
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append({"path": f"{path}.{k}", "hand": a.get(k, "<absent>"), "generated": b.get(k, "<absent>")})
            else:
                json_paths_diff(a[k], b[k], f"{path}.{k}", out, limit)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            json_paths_diff(x, y, f"{path}[{i}]", out, limit)
    elif a != b:
        out.append({"path": path, "hand": a, "generated": b})
    return out


def schemas(gen) -> dict:
    from corpus_structure.core.schemas import render

    adapters = {
        "value.authored": TypeAdapter(gen.AuthoredValue), "value.stored": TypeAdapter(gen.StoredValue),
        "condition.authored": TypeAdapter(gen.AuthoredCondition), "condition.stored": TypeAdapter(gen.StoredCondition),
        "batch.authored": TypeAdapter(gen.AuthoredBatch), "batch.stored": TypeAdapter(gen.StoredBatch),
    }
    (OUT / "schemas").mkdir(exist_ok=True)
    out = {}
    for name, ad in adapters.items():
        text = render(ad)
        (OUT / "schemas" / f"{name}.json").write_text(text)
        committed = (COMMITTED / f"{name}.json").read_text()
        h, g = json.loads(committed), json.loads(text)
        hs, gs = strip(h), strip(g)
        out[name] = {
            "bytes_equal": committed == text,
            "hand_bytes": len(committed.encode()), "generated_bytes": len(text.encode()),
            "equal_without_descriptions": hs == gs and json.dumps(hs) == json.dumps(gs),
            "equal_without_descriptions_any_order": canon(hs) == canon(gs),
            "residue_without_descriptions": json_paths_diff(json.loads(canon(hs)), json.loads(canon(gs))),
            "description_paths_hand": canon(h).count('"description"'),
            "description_paths_generated": canon(g).count('"description"'),
        }
    return out


# ---------------------------------------------------------------------------------------------
# 4. batches
# ---------------------------------------------------------------------------------------------
def errors(model, text: str):
    try:
        obj = model.model_validate_json(text)
        return None, obj
    except ValidationError as e:
        return sorted({(".".join(map(str, x["loc"])), x["type"]) for x in e.errors()}), None


def prefixer():
    """Probe-local migration of S4's stored batches to the current stored form (X2 ruling: prefixed
    names): entity types, predicates, identity slots and qualifier keys get core: when core.yaml declares
    the name, else stat: (the statistics pack's prefix). S4's batches predate the ruling."""
    import yaml
    from s4 import paths

    core = yaml.safe_load(paths.CORE_YAML.read_text())
    core_names = set(core["classes"]) | set(core["slots"])
    pre = lambda n: n if ":" in n else (f"core:{n}" if n in core_names else f"stat:{n}")  # noqa: E731

    def migrate(b: dict) -> dict:
        b = copy.deepcopy(b)
        for e in b.get("entities", []):
            e["type"] = pre(e["type"])
            e["identity"] = {pre(k): v for k, v in (e.get("identity") or {}).items()}
        for c in b.get("claims", []):
            c["predicate"] = pre(c["predicate"])
            if "qualifiers" in c:
                c["qualifiers"] = {pre(k): v for k, v in c["qualifiers"].items()}
        return b

    return migrate


def batches(hb, gen) -> dict:
    from s4 import paths
    from s4.canonical import canonicalize

    migrate = prefixer()

    rows = []
    for set_name, form, files in paths.batch_sets():
        hm = hb.AuthoredBatch if form == "model" else hb.StoredBatch
        gm = gen.AuthoredBatch if form == "model" else gen.StoredBatch
        for f in files:
            raw, _ = paths.load_batch(f)
            canonical, rewrites = canonicalize(raw)
            variants = [("as_written", raw), ("canonical", canonical)]
            if form == "stored":
                variants.append(("canonical_prefixed", migrate(canonical)))
            for variant, b in variants:
                if variant == "canonical" and not rewrites:
                    continue
                text = json.dumps(b, ensure_ascii=False)
                he, ho = errors(hm, text)
                ge, go = errors(gm, text)
                dump_equal = None
                if ho is not None and go is not None:
                    dump_equal = ho.model_dump_json() == go.model_dump_json()
                rows.append({"set": set_name, "unit": f.stem, "form": form, "variant": variant,
                             "hand": "valid" if he is None else "invalid", "generated": "valid" if ge is None else "invalid",
                             "errors_equal": he == ge, "dump_equal": dump_equal,
                             "hand_errors": he[:5] if he else [], "generated_errors": ge[:5] if ge else []})
    files = {(r["set"], r["unit"]) for r in rows}
    return {"batches": len(files), "validations": len(rows),
            "verdicts_agree": sum(r["hand"] == r["generated"] for r in rows),
            "errors_equal": sum(r["errors_equal"] for r in rows),
            "valid_both": sum(r["hand"] == "valid" == r["generated"] for r in rows),
            "dumps_equal": sum(bool(r["dump_equal"]) for r in rows),
            "by_form_verdict": _count(rows), "rows": rows}


def _count(rows):
    c: dict[str, int] = {}
    for r in rows:
        k = f"{r['form']}/{r['variant']}/hand:{r['hand']}/generated:{r['generated']}"
        c[k] = c.get(k, 0) + 1
    return c


# ---------------------------------------------------------------------------------------------
# 5. seeded errors
# ---------------------------------------------------------------------------------------------
def seeded(hb, gen) -> list[dict]:
    from s4 import paths

    base, _ = paths.load_batch(paths.R2 / "reference_model_v1" / "T3.json")
    c0 = lambda b: b["claims"][0]  # noqa: E731

    def setq(b, k, v):
        c0(b).setdefault("qualifiers", {})[k] = v

    seeds = {
        "bad sentence id": lambda b: c0(b)["evidence"][0].__setitem__("sentence", "x1"),
        "empty quote": lambda b: c0(b)["evidence"][0].__setitem__("quote", ""),
        "no evidence": lambda b: c0(b).__setitem__("evidence", []),
        "unknown value tag": lambda b: c0(b).__setitem__("object", {"t": "nope", "v": "1"}),
        "unknown condition op": lambda b: setq(b, "conditions", {"op": "xor", "args": []}),
        "sympy in a batch": lambda b: c0(b).__setitem__("object", {"t": "formula", "latex": "x", "sympy": "x"}),
        "duplicate local ref": lambda b: b["claims"].append(copy.deepcopy(c0(b))),
        "binding without entity": lambda b: c0(b).__setitem__("object", {"t": "formula", "latex": "x",
                                                                           "symbols": {"x": {"bind": "variable"}}}),
        "extra field": lambda b: c0(b).__setitem__("surprise", 1),
        "null optional": lambda b: c0(b).__setitem__("statement", None),
        "non-canonical number": lambda b: c0(b).__setitem__("object", {"t": "number", "v": "01"}),
        "bad modality": lambda b: setq(b, "modality", "maybe"),
    }
    out = []
    for name, mutate in seeds.items():
        b = copy.deepcopy(base)
        mutate(b)
        text = json.dumps(b)
        he, _ = errors(hb.AuthoredBatch, text)
        ge, _ = errors(gen.AuthoredBatch, text)
        out.append({"seed": name, "hand_rejects": he is not None, "generated_rejects": ge is not None,
                    "errors_equal": he == ge, "hand": he, "generated": ge})
    return out


def stock_and_drift() -> dict:
    """The stock gen-pydantic over the same schema, for contrast; and regeneration determinism."""
    from stage_b import generate

    schema = OUT / "schema/core_stage_b.yaml"
    p = subprocess.run([str(Path(sys.executable).parent / "gen-pydantic", ), str(schema)], capture_output=True, text=True)
    (OUT / "generated/stock_gen_pydantic.py").write_text(p.stdout)
    code = p.stdout
    again = generate(schema)
    return {
        "stock_exit": p.returncode,
        "stock_counts": {k: code.count(k) for k in ("discriminator", "MISSING", "frozen", "tuple[", "Optional[", "type ")},
        "stock_phrase_tag": re.findall(r'class PhraseValue\(.*?\n(?:.*\n){0,12}?\s+t: .*', code)[:1],
        "regenerated_identical": again == (OUT / "generated/core_shapes.py").read_text(),
    }


def main() -> int:
    hv, hb, gen = load()
    res = {"features": features(gen), "structure": structure(hv, hb, gen), "schemas": schemas(gen),
           "batches": batches(hb, gen), "seeded": seeded(hb, gen), "stock_and_drift": stock_and_drift()}
    (OUT / "structure.json").write_text(json.dumps(res["structure"], indent=1, default=str) + "\n")
    (OUT / "schemas.json").write_text(json.dumps(res["schemas"], indent=1, default=str) + "\n")
    (OUT / "batches.json").write_text(json.dumps(res["batches"], indent=1, default=str) + "\n")
    (OUT / "seeded.json").write_text(json.dumps(res["seeded"], indent=1, default=str) + "\n")
    summary = {
        "features": res["features"],
        "structure": {k: res["structure"][k] for k in ("compared", "equal", "hand_only", "generated_only")}
        | {"aliases_equal": {k: v["equal"] for k, v in res["structure"]["aliases"].items()},
           "unequal_classes": [r["class"] for r in res["structure"]["classes"] if not r["equal"]]},
        "schemas": {k: {kk: vv for kk, vv in v.items() if kk != "residue_without_descriptions"}
                    for k, v in res["schemas"].items()},
        "batches": {k: v for k, v in res["batches"].items() if k != "rows"},
        "stock_and_drift": res["stock_and_drift"],
        "seeded": {"seeds": len(res["seeded"]), "both_reject": sum(s["hand_rejects"] and s["generated_rejects"] for s in res["seeded"]),
                   "errors_equal": sum(s["errors_equal"] for s in res["seeded"])},
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n")
    print(json.dumps(summary, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
