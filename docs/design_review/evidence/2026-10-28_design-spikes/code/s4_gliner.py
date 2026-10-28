"""S4-D (GLiNER2 part): compile the extraction schema dict and the JointIE schema from the pack
(D2 §7.2), check that gliner2 2.1.0 accepts and round-trips them (OPEN-D2-1), and run one trivial
extraction of each on a trace sentence on CPU with the cached fastino/gliner2.5-base-v1 checkpoint.

    HF_HUB_OFFLINE=1 UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run --locked python code/s4_gliner.py

Writes results/s4/compiled/gliner2/{extraction,joint}.json (the canonical dicts, i.e. the fixpoint of
from_dict/to_dict) and results/s4/gliner2.json (accepted keys, round-trip results, extractions).
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from s4 import paths  # noqa: E402
from s4.pack import Pack  # noqa: E402

SENTENCE = ("Suppose that \\(X\\) is normally distributed with mean \\(\\mu\\) and variance \\(\\sigma^2\\).")  # T3 s1


def words(name: str) -> str:
    return name.replace("_", " ")


def label(pack: Pack, cls: str) -> str:
    return str(pack.sv.get_class(cls).title or words(cls))


def description(pack: Pack, cls: str) -> str:
    el = pack.sv.get_class(cls)
    d = " ".join(str(el.description).split())
    ex = [str(e.value) for e in el.examples]
    return d + (" Examples: " + "; ".join(ex) + "." if ex else "")


def endpoint_labels(pack: Pack, cls: str) -> list[str]:
    """Mention classes that are the class or its descendants (mixins included)."""
    return [label(pack, c) for c in pack.mention_classes() if pack.is_a(c, cls)]


def extraction_dict(pack: Pack) -> dict:
    d: dict = {"entities": {label(pack, c): {"description": description(pack, c)} for c in pack.mention_classes()}}
    for c, a in pack.entity_classes.items():
        if a.get("ci:threshold") is not None:
            d["entities"][label(pack, c)]["threshold"] = a["ci:threshold"]
    attrs, cls_tasks = {}, []
    for n in pack.enums:
        a = {k: v for k, v in __import__("s4.pack", fromlist=["x"]).annotations(pack.sv.get_enum(n)).items()}
        pvs = pack.sv.get_enum(n).permissible_values
        if a.get("ci:extract") == "attribute":
            attrs[n] = {"labels": list(pvs), "applies_to": [label(pack, a["ci:applies_to"])], "qualify_labels": True}
        elif a.get("ci:extract") == "classification":
            cls_tasks.append({"task": n, "labels": {k: " ".join(str(v.description or k).split()) for k, v in pvs.items()}})
    if attrs:
        d["entity_attributes"] = attrs
    if cls_tasks:
        d["classifications"] = cls_tasks
    rel = {words(p): {"description": i.description} for p, i in pack.predicates.items() if i.extract == "relation"}
    if rel:
        d["relations"] = rel
    return d


def joint_schema(pack: Pack):
    from gliner2.joint_ie.schema import JointSchema

    s = JointSchema()
    for c in pack.mention_classes():
        s.entity(label(pack, c), description(pack, c))
    for p, i in pack.predicates.items():
        if i.extract != "relation":
            continue
        s.relation(words(p), head=endpoint_labels(pack, i.domain), tail=endpoint_labels(pack, i.range), description=i.description,
                   unique_head=i.functional, symmetric=i.symmetric)
    s.no_self_loops()
    return s


def main() -> int:
    import gliner2
    from gliner2.inference.schema import Schema
    from gliner2.joint_ie.schema import JointSchema

    pack = Pack()
    out: dict = {"gliner2": gliner2.__version__ if hasattr(gliner2, "__version__") else None, "checkpoint": {
        "repo": "fastino/gliner2.5-base-v1", "revision": paths.GLINER.name}, "sentence": SENTENCE}
    od = paths.COMPILED / "gliner2"
    od.mkdir(parents=True, exist_ok=True)

    d = extraction_dict(pack)
    s = Schema.from_dict(d)
    d1 = s.to_dict()
    d2 = Schema.from_dict(d1).to_dict()
    out["extraction"] = {"compiled_equals_to_dict": d1 == d, "to_dict_is_fixpoint": d1 == d2,
                         "keys_used": sorted(d), "entity_config_keys": sorted({k for v in d["entities"].values() for k in v}),
                         "attribute_keys": sorted({k for v in d.get("entity_attributes", {}).values() for k in v}),
                         "classification_keys": sorted({k for v in d.get("classifications", []) for k in v}),
                         "relation_config_keys": sorted({k for v in d.get("relations", {}).values() for k in v})}
    if d1 != d:
        out["extraction"]["to_dict_differs_at"] = sorted(k for k in set(d) | set(d1) if d.get(k) != d1.get(k))
    try:
        Schema.from_dict({**d, "structure": {}})
        out["extraction"]["unknown_key_rejected"] = False
    except Exception as e:  # noqa: BLE001
        out["extraction"]["unknown_key_rejected"] = f"{type(e).__name__}"
    (od / "extraction.json").write_text(json.dumps(d1, indent=1, ensure_ascii=False) + "\n")

    j = joint_schema(pack)
    jd = j.to_dict()
    jd2 = JointSchema.from_dict(jd).to_dict()
    out["joint"] = {"to_dict_is_fixpoint": jd == jd2, "relations": {k: {kk: v[kk] for kk in ("head", "tail", "directed", "symmetric", "max_per_head") if kk in v}
                                                                     for k, v in jd["relations"].items()},
                    "constraints": jd["constraints"]}
    (od / "joint.json").write_text(json.dumps(jd, indent=1, ensure_ascii=False) + "\n")

    # one trivial extraction each, CPU
    try:
        from gliner2 import AutoExtractor

        t0 = time.perf_counter()
        model = AutoExtractor.from_pretrained(str(paths.GLINER))
        load_s = time.perf_counter() - t0
        t0 = time.perf_counter()
        res = model.extract(SENTENCE, Schema.from_dict(d1), include_spans=True)
        out["extraction_run"] = {"outcome": "passed", "load_s": round(load_s, 1), "extract_s": round(time.perf_counter() - t0, 2),
                                 "result": json.loads(json.dumps(res, default=str))}
    except Exception as e:  # noqa: BLE001
        out["extraction_run"] = {"outcome": "failed", "error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()[-1500:]}
    try:
        from gliner2.joint_ie import JointIE

        t0 = time.perf_counter()
        joint = JointIE.from_pretrained(str(paths.GLINER))
        r = joint.extract(SENTENCE, JointSchema.from_dict(jd))
        out["joint_run"] = {"outcome": "passed", "s": round(time.perf_counter() - t0, 1), "feasible": getattr(r, "feasible", None),
                            "result": json.loads(json.dumps(r.to_dict(), default=str)) if hasattr(r, "to_dict") else str(r)}
    except Exception as e:  # noqa: BLE001
        out["joint_run"] = {"outcome": "failed", "error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()[-1500:]}
    (paths.RES / "gliner2.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str) + "\n")
    print(json.dumps(out, indent=1, ensure_ascii=False, default=str)[:5000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
