"""C source-only adjudication of eleven frozen normal-source quotation facets."""

import json
from hashlib import sha256
from pathlib import Path

from corpus_structure.semantic.identity import canonical_bytes

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
source = json.loads((RAW / "source-opportunities-002.json").read_bytes())
authors = {kind: json.loads((RAW / f"source-author-{kind}-002.json").read_bytes()) for kind in ("A", "B")}
reasons = {
    "normal-density-term": "The whole frozen quotation introduces the named normal density with µ and σ parameters. It includes more than the minimal name; it is not an exact isolated-entity-span rubric.",
    "normal-density-cue": "The cue introduces the immediately adjacent source formula. A uses the earlier general normal name; B locates the local term747–770. Prefer B's local term for any future exact attachment, without rejecting A's valid earlier mention.",
    "normal-density-formula": "The complete selected formula is printed as the normal density after the defining cue. This supports source quotation and local defining role, not independent mathematical verification.",
    "normal-location-parameter": "The passage expressly describes µ as center, and separately attributes its expected-value identification to a Chapter6 demonstration.",
    "normal-scale-parameter": "The passage expressly describes σ as spread and assumes it positive; retain both parts without changing the parameter to variance.",
    "normal-standard-deviation": "The source asserts standard-deviation identification while promising its proof in Chapter6. Preserve that attribution rather than claiming an executed verification.",
    "standard-normal-parameters": "The sentence introduces local Z with µ0 and σ1. Those values specialize this variable, not all normal variables.",
    "standard-normal-definition": "The sentence names a normal variable with preceding parameters standard normal. The anaphoric parameter attachment is supported by immediately preceding Z sentence; no universal identity relation is added.",
    "normal-affine-transform": "The formula X=σZ+µ consumes preceding standard-normal Z and stated µ/σ. Do not detach that premise or use the damaged CDF line as support.",
    "standardization-name": "The complete sentence names conversion of a normal variable to standard normal standardization, not arbitrary normalization of any data.",
    "standardization-transform": "The explicit formula subtracts µ and divides by σ under the preceding normal-X condition; source quotation alone does not prove equivalence for unrelated distributions.",
}
cases = []
for opportunity in source["opportunities"]:
    cases.append({**opportunity, "case_id": "C2-" + opportunity["opportunity_id"],
        "location_judgment": "supported", "role_judgment": "supported",
        "attachment_judgment": "unassessed", "reason": reasons[opportunity["opportunity_id"]]})
result = {"protocol": "wce-source-adjudication-1", "author": "C", "date": "2026-11-06",
    "scope": source["scope"], "parents": {kind: {"file": f"source-author-{kind}-002.json", "sha256": sha256((RAW / f"source-author-{kind}-002.json").read_bytes()).hexdigest()} for kind in ("A", "B")},
    "source_author_input_sha256": sha256((RAW / "source-author-input-002.json").read_bytes()).hexdigest(),
    "original_native_partition": "feature_fit; unchanged", "exposure_use": "already exposed source-family refinement, not new heldout origin",
    "producer_outputs_inspected": False, "cases": cases,
    "disagreements": [
        {"parents": ["A2-01", "B2-001"], "issue": "A locates the general earlier term at71–94; B the local term747–770 beside defining cue795–817.", "disposition": "Both are real mentions; choose B's local term for defining attachment. Earlier mention remains an occurrence with separate anaphoric reasoning."},
        {"parents": ["A2-05", "A2-06", "B2-006"], "issue": "B conservatively marks simulation construction ambiguous because extracted Y line contains injected trailing words.", "disposition": "Keep input-condition and output-parameter text inspectable; complete formula/construction excluded from selected eleven adjudicated facets. No repaired Y formula or scientific correctness claim."},
        {"parents": ["A2-04"], "issue": "CDF coefficient and trailing extraction are corrupt/interrupted.", "disposition": "CDF component remains ambiguous and outside supported selected facets; no mathematical repair from common knowledge."}
    ], "limits": ["Only eleven selected quotation/location/role facets adjudicated; author A11/B12 populations are not silently called complete.", "Endpoint attachments/applicability remain independently unassessed beyond explicit source reasoning; no public-policy witness created.", "No explicit alternate variance parameterization is present in this packet; retain that source gap.", "Native frame/pass binding and evaluator-authorized exposure remain separate obligations."]}
with (RAW / "source-author-C-002.json").open("xb") as stream:
    stream.write(canonical_bytes(result) + b"\n")
print(json.dumps({"outcome": "passed", "cases": len(cases), "parents": {kind: len(value["opportunities"]) for kind, value in authors.items()}}))
