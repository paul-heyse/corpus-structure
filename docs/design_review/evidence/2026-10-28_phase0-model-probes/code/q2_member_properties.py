"""Q-2 (P0-M-Q2): member properties on enum permissible values, native `in_subset` versus a scalar
`ci:properties` annotation.

    UV_PROJECT_ENVIRONMENT=$PWD/build/probe-venv uv run --project \
        docs/design_review/evidence/2026-10-28_phase0-model-probes \
        python docs/design_review/evidence/2026-10-28_phase0-model-probes/code/q2_member_properties.py

Builds three copies of S4's core.yaml under results/q2/schema/ (S4's file is read, never written):
- core_in_subset.yaml: member properties as native permissible-value `in_subset`, the subsets declared;
- core_ci_properties.yaml: the same properties as one scalar `ci:properties` annotation per member;
- core_seeded.yaml: core_in_subset.yaml with one permissible value naming an undeclared subset
  (negative control for the linter rule `no_undeclared_subsets`).
Each file is linted on its own with S4's .linkmllint.yaml (copied beside it), read back through
SchemaView, and the read-back membership is compared with an independent expectation table (EXPECTED,
written here by hand, not derived from either file). The YAML dump of the parsed schema and the
canonical JSON used for the model-revision hash (D2 §2) are checked to keep the declarations.
"""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml
from linkml_runtime.dumpers import json_dumper, yaml_dumper
from linkml_runtime.utils.schemaview import SchemaView

HERE = Path(__file__).resolve().parent
FOLDER = HERE.parent
REPO = FOLDER.parents[3]
S4 = REPO / "docs/design_review/evidence/2026-10-28_design-spikes/results/s4/schema"
SRC = S4 / "domains/core/schema/core.yaml"
LINT_CFG_SRC = S4 / ".linkmllint.yaml"
OUT = FOLDER / "results/q2"
SCHEMA_OUT = OUT / "schema"
BIN = Path(sys.executable).parent

# Independent expectation: property -> {enum: members}. Modality and statement kind follow the plan
# (model-and-projections §3.1) and S4's ci:claim_bearing annotation; segment kinds follow the current
# code (keys.statement_anchor, locators.annotation_units, D3's BM25 predicate). Container membership is
# illustrative (the plan names the property, P0-D-2 fixes members).
EXPECTED: dict[str, dict[str, set[str]]] = {
    "premise_forming": {"ClaimModality": {"supposed"}},
    "attribution_identifying": {"ClaimModality": {"cited"}},
    "conflict_bearing": {"ClaimModality": {"asserted", "defined"}},
    "claim_bearing": {"StatementKind": {"definition", "theorem", "proposition", "lemma", "corollary", "example",
                                        "exercise", "remark", "convention", "notation", "assumption",
                                        "narrative"}},
    "annotation_unit": {"SegmentKind": {"unit", "paragraph"}},
    "statement_anchor": {"SegmentKind": {"unit", "details"}},
    "search_block": {"SegmentKind": {"paragraph", "heading", "list_item", "caption"}},
    "container": {"SegmentKind": {"document", "section", "email_message", "quoted_block"}},
}

SUBSET_DESCRIPTIONS = {
    "premise_forming": "Member property: a claim with this modality forms a premise of its statement.",
    "attribution_identifying": "Member property: a claim with this modality identifies who it is attributed to.",
    "conflict_bearing": "Member property: claims with this modality can conflict with one another.",
    "claim_bearing": "Member property: a statement of this kind bears claims.",
    "annotation_unit": "Member property: a segment of this kind can be an annotation unit.",
    "statement_anchor": "Member property: a segment of this kind anchors a statement's key.",
    "search_block": "Member property: a segment of this kind is a BM25 search block.",
    "container": "Member property: a segment of this kind contains other blocks.",
}

SEGMENT_KINDS = {
    "document": "The whole document.", "section": "A section.", "unit": "An author-marked unit.",
    "paragraph": "A paragraph.", "list": "A list.", "list_item": "A list item.",
    "details": "A details block.", "math_display": "Display math.", "math_inline": "Inline math.",
    "heading": "A heading.", "table": "A table.", "table_row": "A table row.", "table_cell": "A table cell.",
    "caption": "A caption.", "footnote": "A footnote.", "figure": "A figure.", "sentence": "A sentence.",
    "email_message": "An email message.", "quoted_block": "A quoted block in an email.",
    "signature": "An email signature.",
}


def members_of(enum: str) -> dict[str, list[str]]:
    """member -> sorted property names, from EXPECTED."""
    out: dict[str, list[str]] = {}
    for prop, by_enum in EXPECTED.items():
        for m in by_enum.get(enum, ()):
            out.setdefault(m, []).append(prop)
    return {m: sorted(p) for m, p in out.items()}


def build(form: str) -> dict:
    raw = yaml.safe_load(SRC.read_text())
    raw["enums"]["SegmentKind"] = {
        "description": "The kinds of segment (D1 §3.2); a probe copy of the closed set.",
        "permissible_values": {k: {"description": d} for k, d in SEGMENT_KINDS.items()},
    }
    if form == "in_subset":
        for name, desc in SUBSET_DESCRIPTIONS.items():
            raw["subsets"][name] = {"description": desc}
    for enum in ("ClaimModality", "StatementKind", "SegmentKind"):
        pvs = raw["enums"][enum]["permissible_values"]
        for member, pv in pvs.items():
            pv = pvs[member] = dict(pv or {})
            ann = dict(pv.get("annotations") or {})
            ann.pop("ci:claim_bearing", None)  # replaced by the claim_bearing member property
            props = members_of(enum).get(member, [])
            if props and form == "in_subset":
                pv["in_subset"] = props
            if props and form == "ci_properties":
                ann["ci:properties"] = " ".join(props)
            if ann:
                pv["annotations"] = ann
            else:
                pv.pop("annotations", None)
    return raw


def lint(path: Path) -> dict:
    out = path.with_suffix(".lint.json")
    cmd = [str(BIN / "linkml-lint"), "--config", str(path.parent / ".linkmllint.yaml"), "--format", "json",
           "-o", str(out), str(path)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    problems = json.loads(out.read_text() or "[]")
    for pr in problems:
        pr.pop("file", None)
    out.write_text(json.dumps(problems, indent=1, sort_keys=True) + "\n")
    levels: dict[str, int] = {}
    for pr in problems:
        levels[pr["level"]] = levels.get(pr["level"], 0) + 1
    return {"exit": p.returncode, "levels": levels,
            "problems": [f"{pr['level']} {pr['rule_name']}: {pr['message']}" for pr in problems],
            "stderr_tail": p.stderr.strip().splitlines()[-3:]}


def readback(path: Path, form: str) -> dict:
    sv = SchemaView(str(path))
    got: dict[str, dict[str, set[str]]] = {}
    pv_types: set[str] = set()
    for enum in ("ClaimModality", "StatementKind", "SegmentKind"):
        e = sv.get_enum(enum)
        for member, pv in e.permissible_values.items():
            if form == "in_subset":
                props = list(pv.in_subset)
                pv_types |= {type(x).__name__ for x in pv.in_subset}
            else:
                ann = pv.annotations.get("ci:properties")
                val = ann.value if ann is not None else None
                if val is not None:
                    pv_types.add(type(val).__name__)
                props = str(val).split() if val else []
            for p in props:
                got.setdefault(str(p), {}).setdefault(enum, set()).add(member)
    expected = {p: {e: set(m) for e, m in d.items()} for p, d in EXPECTED.items()}
    mism = {p: {"expected": sorted_d(expected.get(p, {})), "got": sorted_d(got.get(p, {}))}
            for p in set(expected) | set(got) if expected.get(p) != got.get(p)}

    # Library accessors that might plausibly expose member properties.
    supposed = sv.get_enum("ClaimModality").permissible_values["supposed"]
    access = {
        "permissible_value_ancestors(supposed, ClaimModality)": sv.permissible_value_ancestors("supposed", "ClaimModality"),
        "permissible_value_parents(supposed, ClaimModality)": sv.permissible_value_parents("supposed", "ClaimModality"),
        "pv.in_subset": [str(x) for x in supposed.in_subset],
        "pv.annotations": {k: v.value for k, v in supposed.annotations.items()},
        "annotation_dict(ClaimModality)": sv.annotation_dict("ClaimModality"),
        "induced_enum(ClaimModality).permissible_values[supposed].in_subset": [
            str(x) for x in sv.induced_enum("ClaimModality").permissible_values["supposed"].in_subset],
    }
    try:
        access["annotation_dict(supposed)"] = sv.annotation_dict("supposed")
    except Exception as ex:  # noqa: BLE001
        access["annotation_dict(supposed)"] = f"{type(ex).__name__}: {ex}"
    subsets = sorted(sv.all_subsets())

    # Round trip: the dumped parsed schema, reparsed, gives the same membership; the canonical JSON
    # used for the revision hash carries the declarations.
    dumped = yaml_dumper.dumps(sv.schema)
    re_raw = yaml.safe_load(dumped)
    pv2 = re_raw["enums"]["SegmentKind"]["permissible_values"]["unit"]
    canon = json.dumps(json.loads(json_dumper.dumps(sv.schema)), sort_keys=True, separators=(",", ":"))
    return {
        "membership_equal_to_expected": not mism,
        "mismatches": mism,
        "value_types": sorted(pv_types),
        "declared_subsets": subsets,
        "accessors": access,
        "yaml_dump_unit": pv2,
        "canonical_json_has_declaration": ("statement_anchor" in canon),
        "canonical_sha256": hashlib.sha256(canon.encode()).hexdigest(),
    }


def sorted_d(d: dict[str, set[str]]) -> dict[str, list[str]]:
    return {k: sorted(v) for k, v in sorted(d.items())}


def generators(path: Path) -> dict:
    """Do stock generators accept the file? (Q-1 and M3 consume these generators.)"""
    out = {}
    for gen in ("gen-json-schema", "gen-pydantic"):
        p = subprocess.run([str(BIN / gen), str(path)], capture_output=True, text=True)
        out[gen] = {"exit": p.returncode, "stdout_bytes": len(p.stdout),
                    "stderr_tail": [ln for ln in p.stderr.strip().splitlines() if "Error" in ln][-2:]}
    return out


def main() -> int:
    SCHEMA_OUT.mkdir(parents=True, exist_ok=True)
    shutil.copy(LINT_CFG_SRC, SCHEMA_OUT / ".linkmllint.yaml")
    files = {}
    for form, name in (("in_subset", "core_in_subset.yaml"), ("ci_properties", "core_ci_properties.yaml")):
        raw = build(form)
        (SCHEMA_OUT / name).write_text(yaml.safe_dump(raw, sort_keys=False, allow_unicode=True, width=110))
        files[form] = SCHEMA_OUT / name
    seeded = copy.deepcopy(yaml.safe_load(files["in_subset"].read_text()))
    seeded["enums"]["SegmentKind"]["permissible_values"]["figure"]["in_subset"] = ["undeclared_property"]
    (SCHEMA_OUT / "core_seeded.yaml").write_text(yaml.safe_dump(seeded, sort_keys=False, allow_unicode=True, width=110))
    shutil.copy(SRC, SCHEMA_OUT / "core_s4_baseline.yaml")

    result: dict = {"source": str(SRC.relative_to(REPO)), "forms": {}}
    result["baseline_lint"] = lint(SCHEMA_OUT / "core_s4_baseline.yaml")
    for form, path in files.items():
        result["forms"][form] = {"file": path.name, "lint": lint(path), "readback": readback(path, form),
                                 "generators": generators(path)}
    result["seeded_lint"] = lint(SCHEMA_OUT / "core_seeded.yaml")
    seeded_hits = [p for p in result["seeded_lint"]["problems"] if "undeclared_property" in p]
    result["seeded_caught"] = bool(seeded_hits) and any(p.startswith("error") for p in seeded_hits)

    (OUT / "result.json").write_text(json.dumps(result, indent=1, sort_keys=True, default=str) + "\n")
    for form, r in result["forms"].items():
        print(form, "lint", r["lint"]["exit"], r["lint"]["levels"], "| membership ok",
              r["readback"]["membership_equal_to_expected"], "| types", r["readback"]["value_types"],
              "| gens", {g: v["exit"] for g, v in r["generators"].items()})
        for p in r["lint"]["problems"]:
            print("   ", p)
    print("baseline lint", result["baseline_lint"]["levels"], "seeded caught", result["seeded_caught"],
          result["seeded_lint"]["problems"])
    print(json.dumps(result["forms"]["in_subset"]["readback"]["accessors"], indent=1, default=str))
    # linkml-lint exits 1 on any warning (--max-warnings 0); the bar is S4's: no errors and only the
    # baseline's own warnings (standard_naming on D1's t and v).
    base = sorted(result["baseline_lint"]["problems"])
    ok = all(not r["lint"]["levels"].get("error") and sorted(r["lint"]["problems"]) == base
             and r["readback"]["membership_equal_to_expected"] for r in result["forms"].values())
    result["passed"] = ok and result["seeded_caught"]
    (OUT / "result.json").write_text(json.dumps(result, indent=1, sort_keys=True, default=str) + "\n")
    print("Q-2", "passed" if result["passed"] else "failed")
    return 0 if ok and result["seeded_caught"] else 1


if __name__ == "__main__":
    sys.exit(main())
