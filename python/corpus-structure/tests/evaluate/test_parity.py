"""S0 parity (evaluation §5 P0-E-2a; record `s0.agreement`).

The spike's stored passes A and B (`results/s0/stored/pass_a`, `pass_b`) are aligned per S0 unit,
A as reference then B, and symmetrized: core 0.933, full 0.627, evidence 0.600 with S0's 13
recorded equivalence decisions (`results/s0/manual_equivalence.tsv`) supplied through the
comparator's test-only decision input. The figures under the product rule (undecided counted
unequal) and the pairs that differ are reported beside them.

The spike's stored dicts are carried into F2b's stored models by the name map (a test-only
adapter: the S0 batches predate the product's stored form), and their anchors become spans
through the frozen S1 segments.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from typing import Any

import pytest

from corpus_structure.core.batch import StoredBatch
from corpus_structure.core.canonical import canonical_json
from corpus_structure.core.tex import token_form
from corpus_structure.evaluate.agreement import symmetrized
from corpus_structure.evaluate.align import AlignmentSide, align

pytestmark = pytest.mark.filterwarnings("error::sympy.utilities.exceptions.SymPyDeprecationWarning")
CORE_QUALIFIERS = {
    "modality",
    "polarity",
    "hedge",
    "attribution",
    "conditions",
    "scope",
    "valid_time",
}


def _values(node: Any, names: dict[str, str]) -> Any:
    """S4 V1: `{"t": "entity", "ref": r}` is the reference `{"ref": r}`; an enum value names its
    enum prefixed."""
    if isinstance(node, dict):
        if node.get("t") == "entity" and "ref" in node:
            return {"ref": node["ref"]}
        if node.get("t") == "enum":
            return {**node, "enum": names[node["enum"]]}
        return {k: _values(v, names) for k, v in node.items()}
    if isinstance(node, list):
        return [_values(v, names) for v in node]
    return node


def stored(raw: dict[str, Any], names: dict[str, str]) -> StoredBatch:
    raw = _values({k: v for k, v in raw.items() if k != "envelope"}, names)
    for s in raw.get("statements", []):
        s["kind"] = names.get(s["kind"], s["kind"])
    for e in raw.get("entities", []):
        e["type"] = names[e["type"]]
        e["identity"] = {names[k]: v for k, v in (e.get("identity") or {}).items()}
    for c in raw.get("claims", []):
        c["predicate"] = names[c["predicate"]]
        c["qualifiers"] = {
            (f"core:{k}" if k in CORE_QUALIFIERS else names[k]): v
            for k, v in (c.get("qualifiers") or {}).items()
        }
    raw["rendition"] = raw.get("rendition") or "ren:" + "0" * 32
    return StoredBatch.model_validate(raw)


def sides(env: Any, folder: str, unit: str, sample: dict[str, Any]) -> AlignmentSide:
    meta = sample["units"][unit]
    name = meta["page"].replace("/", "__").removesuffix(".html")
    segments = [
        json.loads(x)
        for x in (env.spike / "results/s1/segments" / f"{name}.jsonl").read_text().splitlines()
    ]
    spans = {s["key"]: (s["start"], s["end"]) for s in segments}
    sentences = []
    for p in meta["parts"]:
        spans[p["segment_key"]] = (p["start"], p["end"])
        for s in p["sentences"]:
            spans[s["key"]] = (s["start"], s["end"])
            sentences.append((s["start"], s["end"]))
    raw = json.loads((env.spike / "results/s0/stored" / folder / f"{unit}.json").read_text())
    batch = stored(raw, env.statistics()[1])
    anchors = {s.local_ref: tuple(spans[k] for k in s.anchor) for s in batch.statements}
    return AlignmentSide(unit, batch, anchors, tuple(sentences))


def decisions(env: Any) -> dict[tuple[str, str], bool]:
    out = {}
    path = env.spike / "results/s0/manual_equivalence.tsv"
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            a, b = (
                canonical_json({"latex": token_form(x, {}), "t": row["kind"]}).decode()
                for x in (row["a"], row["b"])
            )
            out[(a, b)] = row["decision"] == "equal"
    return out


def agreement(env: Any, decided: dict[tuple[str, str], bool] | None) -> tuple[Any, list[Any]]:
    sample = json.loads((env.spike / "sample.json").read_text())
    ab, ba, undecided, tiers_used = [], [], [], Counter()
    for unit in sample["units"]:
        a, b = sides(env, "pass_a", unit, sample), sides(env, "pass_b", unit, sample)
        ctx = env.context(env.view(sample["units"][unit]["page"]).macros, decisions=decided)
        ab.append(align(a, b, ctx))
        ba.append(align(b, a, ctx))
        undecided += [(unit, e.a, e.b, e.detail) for e in ctx.comparator.undecided]
        tiers_used.update(e.tier.value for e in ctx.comparator.log)
    print(f"\nvalue comparisons by deciding tier: {dict(tiers_used)}")
    return symmetrized(ab, ba), undecided


def test_s0_parity_with_the_recorded_decisions(env: Any) -> None:
    tiers, undecided = agreement(env, decisions(env))
    got = {t: round(v.agreement or 0.0, 3) for t, v in tiers.items()}
    print(f"\nS0 agreement with the recorded decisions: {got}; undecided {len(undecided)}")
    assert got == {"core": 0.933, "full": 0.627, "evidence": 0.6}


def test_s0_under_the_product_rule(env: Any) -> None:
    """Undecided comparisons count unequal: reported beside the parity figures."""
    tiers, undecided = agreement(env, None)
    got = {t: round(v.agreement or 0.0, 3) for t, v in tiers.items()}
    print(f"\nS0 agreement under the product rule: {got}")
    for row in sorted(set(undecided)):
        print("   undecided", *row)
    assert got["core"] <= 0.933 + 1e-9
