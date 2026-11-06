"""C output-first source/location/role judgments, retaining independent grain."""

import json
from collections import Counter
from hashlib import sha256
from pathlib import Path

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
inspection = json.loads((HERE / "candidates009/wce-statistics-normal-20261106/inspection.json").read_bytes())
source = json.loads((RAW / "source-author-input-002.json").read_bytes())["passages"][0]["text"]
authors = {kind: json.loads((RAW / f"output-author-{kind}-001.json").read_bytes()) for kind in ("A", "B")}
parents = {"A": {r["contribution_id"]: r for r in authors["A"]["items"]}, "B": {r["contribution_id"]: r for r in authors["B"]["judgments"]}}
contributions = [r["row"] for r in inspection["items"] if r["population"] == "contribution"]
if any(set(values) != {r["contribution_id"] for r in contributions} for values in parents.values()):
    raise ValueError("independent author population differs from exact frozen output membership")
items = []
for row in contributions:
    value = source_python(row["value"])
    texts = [source[start:end] for start, end in value["extents"]]
    if texts != [a["source_piece"] for a in row["anchors"]]:
        raise ValueError("C cannot support a source location whose independent projection text differs")
    raw_match = row["semantic_type"].startswith("source_rule.")
    bad_term = row["semantic_type"] == "source_role.term" and texts == ["σ"]
    if raw_match:
        role, reason = "unassessed", "Raw attributed pattern output is not itself a linguistic-role assertion; inspect its embedded role proposals separately."
    elif bad_term:
        role, reason = "unsupported", "At793–794 σ is a parameter within the phrase with parameters µ and σ. The defined subject is the normal density function; σ is not the defined target of this passive_named construction."
    elif value["role"] == "naming_cue":
        role, reason = "supported", "Called explicitly introduces a name in the inspected source context; this establishes a naming cue only."
    elif value["role"] == "defining_cue":
        role, reason = "supported", "Defined/is-defined-as introduces the local normal-density formula. Cue correctness does not establish the target-term role or definition applicability."
    elif value["role"] == "condition_cue":
        role, reason = "supported", "The inspected if occurs in explicit conditional language. The full condition/consequent, necessity and applicability remain separate questions."
    else:
        raise ValueError("C has not independently authored a judgment for this role")
    group_wrong = raw_match and value["rule"] == "definition" and any(r["role"] == "term" and r["extents"] == [[793, 794]] for r in value["roles"])
    items.append({"contribution_id": row["contribution_id"], "semantic_type": row["semantic_type"],
        "location_judgment": "supported", "expected_source_pieces": texts, "projection_extents": value["extents"],
        "location_scope": "independently checked supplied source projection; native pointer/local-offset correctness unassessed by these source-only authors",
        "role_judgment": role, "role_reason": reason,
        "embedded_role_group_judgment": "unsupported" if group_wrong else "not_separately_adjudicated",
        "embedded_role_group_reason": "Defining cue remains supported but grouped σ-as-defined-term interpretation is wrong; the raw match's quoted token locations remain valid." if group_wrong else None,
        "attachment": "unassessed", "applicability": "unassessed", "scientific_truth": "unassessed",
        "parent_A_location": parents["A"][row["contribution_id"]]["source_location"]["status"],
        "parent_A_role": parents["A"][row["contribution_id"]]["linguistic_role"]["status"],
        "parent_B_location": parents["B"][row["contribution_id"]]["source_location"]["status"],
        "parent_B_role": parents["B"][row["contribution_id"]]["linguistic_role"]["status"]})
result = {"protocol": "wce-independent-output-adjudication-1", "author": "C", "date": "2026-11-06",
    "run_id": 113, "source_projection_correspondence": "original native sourceview48 and current view53 share exact source projection/native product; parent input retains original custody",
    "parents": {kind: {"file": f"output-author-{kind}-001.json", "sha256": sha256((RAW / f"output-author-{kind}-001.json").read_bytes()).hexdigest()} for kind in ("A", "B")},
    "items": items, "counts": {"source_location": dict(Counter(r["location_judgment"] for r in items)), "linguistic_role": dict(Counter(r["role_judgment"] for r in items)), "raw_group_role_errors": sum(r["embedded_role_group_judgment"] == "unsupported" for r in items)},
    "disposition": "A assesses raw presence and individual roles; B additionally rolls the unsupported embedded σ-term into the raw definition-group judgment. Preserve both grains; neither valid raw coordinates nor a valid defining cue repairs that wrong term role.",
    "quality_claim": "exact selected outputs and declared source projection only; no percentage, corpus-general efficacy, native-pointer-independent verification or public policy activation"}
with (RAW / "output-author-C-001.json").open("xb") as stream:
    stream.write(canonical_bytes(result) + b"\n")
print(json.dumps({"outcome": "passed", "items": len(items), "counts": result["counts"]}))
