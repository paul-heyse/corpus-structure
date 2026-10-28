"""S0-R2: annotator inputs v1 — guideline v1, a reference generated from the schema, the format with
exact value shapes, worked examples, and unit packets whose standing context is a query.

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/s0r2_inputs.py

Writes results/s0r2/inputs/packet_v1/ (packet-only: no page texts; passes SV and HV) with
guideline.md, reference.md, format.md, units/*.md (core and held-out units in one list, not
labelled as such), and instructions_<pass>.md. schema.yaml and model.md are kept as background.
The worked examples (results/s0r2/examples/E*.json, written by the root for units on a page no
test unit uses) are embedded in reference.md with their packets.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import yaml

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))
from s0a_packets import FORMAT, section  # noqa: E402

EVIDENCE = CODE.parent
REPO = EVIDENCE.parents[3]
R2 = EVIDENCE / "results" / "s0r2"
SAMPLE = json.loads((R2 / "sample.json").read_text())
GUIDELINE = EVIDENCE / "s0r2" / "guideline_v1.md"
SCHEMAS = [CODE / "schema" / "core.yaml", CODE / "schema" / "statistics.yaml"]
STRUCTURAL = ["defines", "proves", "refers_to", "follows_from"]
FORM = ["defined_as", "construction_formula", "definition_formula", "transformation_of", "has_parameter",
        "parameter_domain", "parameter_role", "derived_parameter", "identical_parameter", "special_case_of"]
VALIDATE = ("cd /home/paul/corpus-structure/docs/design_review/evidence/2026-10-28_design-spikes && "
            "S0_SAMPLE=results/s0r2/sample.json UV_PROJECT_ENVIRONMENT=/home/paul/corpus-structure/build/spike-venv "
            "uv run python code/s0_check.py {out} --rules")


def name_of(page: str) -> str:
    return page.replace("/", "__").removesuffix(".html")


def load(meta: dict):
    d = EVIDENCE / meta["rendition_dir"]
    n = name_of(meta["page"])
    text = (d / "canonical" / f"{n}.txt").read_text(encoding="utf-8")
    segs = [json.loads(x) for x in (d / "segments" / f"{n}.jsonl").read_text().splitlines()]
    return text, segs


def titles() -> dict:
    out = json.loads((EVIDENCE / "results" / "s1" / "renditions.json").read_text())
    out.update(json.loads((R2 / "s1" / "renditions.json").read_text()))
    return {p: r["title"] for p, r in out.items()}


def packet(uid: str, meta: dict, title: str) -> str:
    text, segs = load(meta)
    by_key = {s["key"]: s for s in segs}
    first = meta["parts"][0]
    secs, s = [], by_key[first["segment_key"]]
    while s["parent"]:
        s = by_key[s["parent"]]
        if s["kind"] == "section":
            secs.append(s)
    path = " › ".join(text[x["start"]:x["end"]].split("\n", 1)[0] for x in reversed(secs))
    hint = by_key[first["segment_key"]]["attrs"].get("hint", {}).get("statement_kind")
    head = f"# Unit {uid}  ·  {title} › {path}" + (f"  ·  the source marks it: {hint}" if hint else "")
    lines = [head, "", "## Standing context",
             "Sentences outside the unit that it depends on: where symbols it uses were introduced and are "
             "still in force, and section-wide suppositions. Cite them as `cN` (guideline §10.2).", ""]
    lines += [f"[{c['id']}] {text[c['start']:c['end']]}" for c in meta["context"]] or ["(none)"]
    lines += ["", "## Text"]
    for p in meta["parts"]:
        heads = [x for x in segs if x["kind"] == "heading" and p["start"] <= x["start"] and x["end"] <= p["end"]]
        items = [(x["start"], "s", x) for x in p["sentences"]] + [(h["start"], "h", h) for h in heads]
        for _, kind, x in sorted(items, key=lambda i: i[0]):
            lines.append(f"--- {text[x['start']:x['end']]} ---" if kind == "h" else f"[{x['id']}] {text[x['start']:x['end']]}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------------- reference.md


def schema() -> dict:
    merged = {"classes": {}, "slots": {}, "enums": {}}
    for f in SCHEMAS:
        d = yaml.safe_load(f.read_text())
        for k in merged:
            merged[k].update(d.get(k) or {})
    return merged


def ann(x: dict) -> dict:
    return x.get("annotations") or {}


GROUP_RULES = {
    "structural": ("no `statement_role`", "`asserted`", "none"),
    "form": ("`definiens` in a definition or for a formula introducing a variable; otherwise as §10.3",
             "`defined` when stipulated, `asserted` when concluded",
             "no `claim` nodes; only restrictions stated with it on its own symbols (§10.7 rule 2)"),
    "other": ("by statement kind (§10.3): `premise`, `definiens`, `conclusion` or `example_value`",
              "by role (§10.6)",
              "premises and example values: none but an index range (rule 1); otherwise a `claim` node per premise "
              "it depends on and every stated restriction on its symbols (rule 3)"),
}


def card(name: str, sl: dict, classes: dict, used: dict) -> list[str]:
    a = ann(sl)
    obj = a.get("ci:object", "entity")
    rng = sl.get("range", "")
    shape = {"entity": f'`{{"ref": <local ref of a {rng}>}}`', "formula": '`{"t": "formula", "latex": …, "symbols": {…}}`',
             "set": '`{"t": "set", "latex": …, "symbols": {…}}`', "enum": f"an `{rng}` value", "phrase": '`{"t": "phrase", "text": …}`'
             }.get(obj, f"`{obj}`")
    group = "structural" if name in STRUCTURAL else "form" if name in FORM else "other"
    role, mod, cond = GROUP_RULES[group]
    quals = a.get("ci:qualifiers") or []
    out = [f"#### `{name}`", "",
           f"- **Subject:** {sl.get('domain', 'Entity')}. **Object:** {rng} as {shape}.",
           f"- **Meaning:** {' '.join(str(sl.get('description', '')).split())}"]
    if quals:
        out.append(f"- **Its qualifiers:** {', '.join(f'`{q}`' for q in quals)} (besides the core qualifiers).")
    if a.get("ci:functional"):
        out.append("- **One value per subject** in a statement.")
    out += [f"- **Role:** {role}. **Modality:** {mod}.", f"- **Conditions:** {cond}."]
    if used.get(name):
        out.append(f"- **In the worked examples:** {', '.join(used[name])}.")
    return out + [""]


def reference(examples: dict, packets: dict) -> str:
    sch = schema()
    used: dict[str, list[str]] = {}
    for eid, b in examples.items():
        for c in b.get("claims", []):
            used.setdefault(c["predicate"], []).append(f"{eid} `{c['local_ref']}`")
    L = ["# Annotation reference (generated from the schema; guideline v1 §10.10)", "",
         "Look things up here while annotating: which entity type, which predicate, which qualifiers, how to",
         "bind a symbol, the exact shape of every value. The guideline says what to capture; this says how to",
         "write it. `schema.yaml` and `model.md` are the sources, for background only.", "",
         "## 1. Entity types", "", "| Type | What it is | Scope | Identity slots | Examples |", "|---|---|---|---|---|"]
    for cname, c in sch["classes"].items():
        a = ann(c)
        if a.get("ci:kind") != "entity" or cname == "Statement":
            continue
        L.append(f"| `{cname}` | {' '.join(str(c.get('description', '')).split())} | {a.get('ci:scope', '')} | "
                 f"{', '.join(a.get('ci:identity_keys', [])) or '—'} | {', '.join(map(str, a.get('ci:examples', []))) or '—'} |")
    L += ["", "A `Statement` is listed in `statements[]`, not `entities[]`: `{local_ref, kind, anchor}`.", "",
          "## 2. Predicates", "",
          "Grouped by how they take roles, modality and conditions (guideline §10.3, §10.6, §10.7).", ""]
    preds = {k: v for k, v in sch["slots"].items() if ann(v).get("ci:role") == "predicate" and k != "unschematized"}
    for title, names in (("Structural claims (about statements)", STRUCTURAL),
                         ("Formula and family-structure claims", [p for p in FORM if p in preds]),
                         ("Everything else", [p for p in preds if p not in STRUCTURAL and p not in FORM])):
        L += [f"### {title}", ""]
        for p in names:
            L += card(p, preds[p], sch["classes"], used)
    L += ["## 3. Qualifiers", "", "| Qualifier | Value | Meaning |", "|---|---|---|"]
    for k, v in sch["slots"].items():
        if ann(v).get("ci:role") == "qualifier":
            L.append(f"| `{k}` | {v.get('range', '')}{' (list)' if v.get('multivalued') else ''} | "
                     f"{' '.join(str(v.get('description', '')).split())} |")
    L += ["", "## 4. Enumerations", ""]
    for k, v in sch["enums"].items():
        vals = v.get("permissible_values") or {}
        L.append(f"- **{k}:** " + "; ".join(
            f"`{n}`" + (f" ({' '.join(str((d or {}).get('description', '')).split())})" if (d or {}).get("description") else "")
            for n, d in vals.items()))
    L += ["", "## 5. Values and condition nodes", "",
          "| Value | Shape |", "|---|---|",
          '| Formula | `{"t": "formula", "latex": "b Z", "symbols": {"b": <binding>, "Z": <binding>}}` |',
          '| Set | `{"t": "set", "latex": "(0, \\\\infty)", "symbols": {}}` |',
          '| Number | `{"t": "number", "v": "1.2", "unit": null}` (only where a slot takes numbers; parameter values are formulas) |',
          '| Phrase | `{"t": "phrase", "text": "…", "sentence": "s2"}` |',
          '| Entity | `{"ref": "<local_ref>"}` |',
          '| Parameter values | `{"shape": <formula>, "scale": <formula>}`, keyed by canonical parameter names (§10.4) |',
          "", "| Binding | Shape |", "|---|---|",
          '| variable | `{"bind": "variable", "entity": "<local_ref>"}` |',
          '| param_of, param_expr_of | `{"bind": "param_of", "claim": "<claim local_ref>", "param": "<canonical name>"}` |',
          '| family_param | `{"bind": "family_param", "entity": "<FamilyParameter local_ref>"}` |',
          '| free, constant, unresolved | `{"bind": "free"}` |',
          "", "Which binding applies is the table in guideline §10.7; symbol keys carry no backslash.", "",
          "| Condition node | Shape |", "|---|---|",
          '| and, or | `{"op": "and", "args": [<node>, …]}` |',
          '| not | `{"op": "not", "arg": <node>}` |',
          '| claim | `{"op": "claim", "ref": "<claim local_ref>"}` |',
          '| member | `{"op": "member", "x": <formula>, "set": <set>}` |',
          '| cmp | `{"op": "cmp", "rel": "<" | "<=" | "=" | "!=" | ">" | ">=", "lhs": <formula>, "rhs": <formula>}` |',
          '| pred | `{"op": "pred", "name": "independent", "args": [{"ref": "<local_ref>"}, …]}` |',
          '| phrase | `{"op": "phrase", "text": "…", "sentence": "s3"}` |',
          '| unsupported | `{"op": "unsupported", "text": "…", "reason": "…"}` |',
          "", "## 6. Worked examples", "",
          "Three units from a page no annotation unit comes from, annotated under guideline v1.", ""]
    for eid in sorted(examples):
        L += [f"### {eid}", "", "Packet:", "", "```text", packets[eid].rstrip(), "```", "", "Batch:", "", "```json",
              json.dumps(examples[eid], indent=1, ensure_ascii=False), "```", ""]
    return "\n".join(L) + "\n"


FORMAT_V1 = FORMAT.split("Notes that are part of this format:")[0] + """Notes that are part of this format:

- `unit_ref` is the unit id given in the packet header (e.g. "U5").
- Evidence cites a sentence of the unit (`sN`) or of its standing context (`cN`) and a quote that is
  an exact substring of that sentence.
- A statement's `anchor` is `"unit"` or a list of sentence ids (`["s1", "s2"]`, or `["c1"]` for a
  context premise's assumption statement, guideline §10.2).
- `extent` on a local entity is `statement` or `section` (guideline §10.4).
- `identity` holds the class's identity slots (`reference.md` §1); an entity-valued slot is a local
  ref string: `{"family": "G", "canonical_name": "shape"}`.
- `aliases` is a list of strings.
- `scope` (a qualifier) is a string: `"statement"` or `"section"`.
- Values, bindings and condition nodes have the exact shapes in `reference.md` §5.
- `alternatives` lists groups of claim local refs that are competing readings, with a one-line reason.
- `unsupported` records text the schema cannot state: `{local_ref, sentence, quote, reason}`.
- Evidence roles: `primary`, `supporting`, `condition`, `definition`.
"""

INSTRUCTIONS = """# Instructions for annotation pass {PASS}

You are one of several independent annotators. Annotate each unit following the guideline exactly.
Your work is compared with other annotators' later; do not try to guess what anyone else would write.

## Read, in this order

1. `guideline.md` — what to capture and the rules for roles, modality, conditions and bindings.
2. `reference.md` — entity types, every predicate with how it takes roles and conditions, qualifiers,
   value shapes, and three complete worked examples. Keep it open while you annotate.
3. `format.md` — the output format.
4. `units/<unit>.md` — one packet per unit: its standing context (`cN`) and its text (`sN`).

`schema.yaml` and `model.md` are the sources `reference.md` is generated from; open them only if the
reference does not answer a question, and say so in your notes.

## Do

For each of the {N} units in `units/` ({UNITS}):

1. Annotate the unit into one model-facing `ClaimProposalBatch` and write it to `{OUT}/<unit>.json`.
2. Write `{OUT}/notes/<unit>.md`: every point where you had to guess, naming the guideline section
   that was unclear; anything the schema could not express beyond what you recorded as `unsupported`.
3. Validate: `{VALIDATE}`. It reports format and invariant issues (fix them) and guideline-rule
   warnings (fix them unless you are sure the rule does not apply, and then say why in your notes).
   Before fixing anything, copy your first version of each batch to `{OUT}/first/<unit>.json`.

When all are done, write `{OUT}/opened_files.txt`: every file you opened or searched, one per line.

## Do not read

Anything outside this input folder and your output folder: no design documents, no other results
folders, no other annotator's output, no code, no Git history, no directory listings outside these two
folders. If you believe you need something else, stop and say so in your final report.

## Report

Finish with a short report: units completed, validation outcome per unit, and the three guideline
points you found least clear.
"""


def main() -> int:
    t = titles()
    packets = {u: packet(u, m, t[m["page"]]) for u, m in SAMPLE["units"].items()}
    examples = {}
    for u, m in SAMPLE["units"].items():
        f = R2 / "examples" / f"{u}.json"
        if m["set"] == "example" and f.exists():
            examples[u] = json.loads(f.read_text())
    out = R2 / "inputs" / "packet_v1"
    if out.exists():
        shutil.rmtree(out)
    (out / "units").mkdir(parents=True)
    (R2 / "inputs" / "example_packets").mkdir(parents=True, exist_ok=True)
    (out / "guideline.md").write_text(GUIDELINE.read_text())
    (out / "reference.md").write_text(reference(examples, packets))
    (out / "format.md").write_text(FORMAT_V1.replace("{D2_7_3}", re.search(
        r"```text\n(ClaimProposalBatch.*?)```", section(REPO / "docs/design/D2-schema-and-guidelines.md", "### 7.3", "### 7.4"),
        re.S).group(1).rstrip()))
    (out / "schema.yaml").write_text("# core and statistics schema v0, verbatim (background for reference.md)\n"
                                     + "\n---\n".join(f.read_text() for f in SCHEMAS))
    (out / "model.md").write_text("<!-- Verbatim: docs/design/D1-knowledge-representation.md §1–§11 (background) -->\n\n"
                                  + section(REPO / "docs/design/D1-knowledge-representation.md", "## 1. Scope and design goals",
                                            "## 12. Worked example"))
    units = [u for u, m in SAMPLE["units"].items() if m["set"] in ("core", "held_out")]
    for u in units:
        (out / "units" / f"{u}.md").write_text(packets[u])
    for u, m in SAMPLE["units"].items():
        if m["set"] == "example":
            (R2 / "inputs" / "example_packets" / f"{u}.md").write_text(packets[u])
    for pas in ("sv", "hv"):
        o = f"results/s0r2/pass_{pas}"
        (out / f"instructions_{pas}.md").write_text(INSTRUCTIONS.format(
            PASS=pas.upper(), OUT=o, N=len(units), UNITS=", ".join(units), VALIDATE=VALIDATE.format(out=o)))
    print("wrote", out, "examples:", sorted(examples))
    return 0


import re  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
