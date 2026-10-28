"""S0-A: blind annotation packets (D7 §3.2 golden mode) for passes A and B, and pass P later.

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/s0a_packets.py [golden|packet_only]

golden (default): results/s0/inputs/golden/ — guideline, schema, model, format, unit packets and
page texts. packet_only: results/s0/inputs/packet_only/ — the same without page texts (pass P).
Sources are copied verbatim from the design documents named in each file's header.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

import yaml

CODE = Path(__file__).resolve().parent
EVIDENCE = CODE.parent
REPO = EVIDENCE.parents[3]
DESIGN = REPO / "docs/design"
S1 = EVIDENCE / "results" / "s1"
SAMPLE = json.loads((EVIDENCE / "sample.json").read_text())
METHODS = yaml.safe_load(re.search(r"### 12\.1 `methods\.yaml`\n\n```yaml\n(.*?)\n```",
                                   (DESIGN / "D2-schema-and-guidelines.md").read_text(), re.S).group(1))
BINDERS = METHODS["binders"]


def section(path: Path, start: str, stop: str | None) -> str:
    """Lines from the heading `start` up to (not including) the heading `stop`."""
    text = path.read_text()
    i = text.index(start)
    j = text.index(stop, i) if stop else len(text)
    return text[i:j].rstrip() + "\n"


def name_of(page: str) -> str:
    return page.replace("/", "__").removesuffix(".html")


def load(page: str) -> tuple[str, list[dict], list[dict]]:
    n = name_of(page)
    text = (S1 / "canonical" / f"{n}.txt").read_text(encoding="utf-8")
    segs = [json.loads(x) for x in (S1 / "segments" / f"{n}.jsonl").read_text().splitlines()]
    sents = [json.loads(x) for x in (S1 / "sentences" / f"{n}.provisional.jsonl").read_text().splitlines()]
    return text, segs, sents


def section_path(seg_key: str, by_key: dict, text: str) -> list[dict]:
    out = []
    s = by_key[seg_key]
    while s["parent"]:
        s = by_key[s["parent"]]
        if s["kind"] == "section":
            out.append(s)
    return list(reversed(out))


def is_binding(sentence: str) -> bool:
    words = re.findall(r"[A-Za-z]+", sentence.lower())
    if words and words[0] in BINDERS["sentence_initial"]:
        return True
    low = sentence.lower()
    return any(p in low for p in BINDERS["section_wide"])


def standing_context(start: int, sections: list[dict], sents: list[dict], text: str) -> list[str]:
    """D7 §3.2 golden mode: previous binding sentences in the same (innermost) section, at most five,
    computed from the text alone."""
    if not sections:
        lo = 0
    else:
        lo = sections[-1]["start"]
    prior = [s for s in sents if lo <= s["start"] and s["end"] <= start]
    binding = [text[s["start"]:s["end"]] for s in prior if is_binding(text[s["start"]:s["end"]])]
    return binding[-5:]


def unit_packet(uid: str, meta: dict, title: str) -> str:
    page = meta["page"]
    text, segs, sents = load(page)
    by_key = {s["key"]: s for s in segs}
    first = meta["parts"][0]
    secs = section_path(first["segment_key"], by_key, text)
    path = " › ".join(text[s["start"]:s["end"]].split("\n", 1)[0] for s in secs)
    unit_seg = by_key[first["segment_key"]]
    hint = unit_seg["attrs"].get("hint", {}).get("statement_kind")
    kind = " + ".join(p["kind"] for p in meta["parts"])
    head = f"# Unit {uid}  ·  {title} › {path}  ·  kind: {kind}" + (f", statement kind: {hint}" if hint else "")
    lines = [head, "", "## Standing context"]
    ctx = standing_context(first["start"], secs, sents, text)
    lines += [f"[c{i + 1}] {c}" for i, c in enumerate(ctx)] or ["(none)"]
    lines += ["", "## Text"]
    for p in meta["parts"]:
        # headings inside the unit (a details block's summary, e.g. "Details:") are shown unnumbered
        heads = [s for s in segs if s["kind"] == "heading" and p["start"] <= s["start"] and s["end"] <= p["end"]]
        items = [(s["start"], "s", s) for s in p["sentences"]] + [(h["start"], "h", h) for h in heads]
        for _, kind, s in sorted(items, key=lambda x: x[0]):
            if kind == "h":
                lines.append(f"--- {text[s['start']:s['end']]} ---")
            else:
                lines.append(f"[{s['id']}] {text[s['start']:s['end']]}")
    lines += ["", f"<!-- rendition {meta['rendition_key']}; parts: "
              + "; ".join(f"{p['kind']} {p['start']}–{p['end']}" for p in meta["parts"]) + " -->", ""]
    return "\n".join(lines)


def page_text(page: str, units_here: dict[str, dict]) -> str:
    """The page's canonical text with every sentence numbered [pN] and the units to annotate marked."""
    text, segs, sents = load(page)
    starts = {}
    for uid, meta in units_here.items():
        for i, p in enumerate(meta["parts"]):
            starts.setdefault(p["start"], []).append(f"<<< UNIT {uid} part {i + 1} begins >>>")
            starts.setdefault(p["end"], []).append(f"<<< UNIT {uid} part {i + 1} ends >>>")
    out, pos = [], 0
    marks = sorted(set(starts) | {s["start"] for s in sents})
    sent_at = {s["start"]: i + 1 for i, s in enumerate(sents)}
    for m in marks:
        out.append(text[pos:m])
        for note in starts.get(m, []):
            out.append(f"\n{note}\n")
        if m in sent_at:
            out.append(f"[p{sent_at[m]}] ")
        pos = m
    out.append(text[pos:])
    return f"# {page} (canonical text; [pN] numbers page sentences for reference only)\n\n" + "".join(out) + "\n"


FORMAT = """# Output format: ClaimProposalBatch, model-facing form

Write one JSON object per unit, following the model-facing form below (from D2 §7.3). Cite
evidence by **sentence id and quote**: the sentence ids are the `[sN]` labels in the unit's
packet; a quote is an exact substring of that sentence (copy LaTeX exactly as written). Do not
give character offsets.

```text
{D2_7_3}
```

Notes that are part of this format:

- `unit_ref` is the unit id given in the packet header (e.g. "U5").
- `extent` on a local entity is `statement` (scoped to the statement that binds it) or `section`
  (the enclosing section, from the binding sentence on), as D1 §4.2 and the guideline describe.
- Values are D1 §6 tagged objects (`{{"t": "formula", "latex": "…", "symbols": {{…}}}}` etc.);
  condition trees are D1 §7 nodes keyed by `op`; `claim` nodes and symbol bindings use local refs.
- `alternatives` lists groups of claim local refs that are competing readings of the same text,
  with a one-line reason (guideline §10.8).
- `unsupported` records text the schema cannot state, with a reason (guideline §10.5).
- Evidence roles: `primary`, `supporting`, `condition`, `definition` (D1 §5.1).
"""

INSTRUCTIONS = """# Instructions for annotation pass {PASS}

You are one of several independent annotators. Annotate the core units of this spike following
the guideline exactly. Your work is compared with other annotators' later; do not try to guess
what anyone else would write.

## Read

1. `guideline.md` (the annotation guideline, v0) — this governs what you capture.
2. `schema.yaml` (core and statistics schema v0: classes, predicates, qualifiers, enums).
3. `model.md` (the knowledge model: entities, claims, qualifiers, values, conditions, statuses).
4. `format.md` (the output format).
5. For each unit: `units/<unit>.md` (the unit packet; lines like `--- Details: ---` are headings
   inside the unit, such as the summary of a collapsible proof or solution){PAGES_LINE}

## Do

For each of the twelve units in `units/` ({UNITS}):

1. Annotate the unit into one model-facing `ClaimProposalBatch` and write it to
   `{OUT}/<unit>.json` (e.g. `{OUT}/T1.json`).
2. Write `{OUT}/notes/<unit>.md`: every point where you had to guess, naming the guideline
   section that was unclear; any text that looks mis-rendered (garbled, missing words, odd
   markers); anything the schema could not express beyond what you recorded as `unsupported`.
3. Validate your batch and its quotes:
   `{VALIDATE}`
   Before fixing anything, copy your first version of each batch to `{OUT}/first/<unit>.json`.
   Then fix malformed output and unlocated quotes, and validate again.

When all twelve are done, write `{OUT}/opened_files.txt`: every file you opened or searched,
one path per line.

## Do not read

Anything outside this input folder and your output folder, in particular: `docs/design/` (all
design documents, including the worked trace), any other annotator's output under
`results/s0/`, the repository `corpus-intelligence`, and Git history. The files in this input
folder are your only sources for the text. If you believe you need something else, stop and
say so in your final report instead of looking for it.

## Report

Finish with a short report: units completed, validation outcome per unit, total time spent on
guessing, and the three guideline points you found least clear.
"""


def main(mode: str) -> int:
    out = EVIDENCE / "results" / "s0" / "inputs" / mode
    if out.exists():
        shutil.rmtree(out)
    (out / "units").mkdir(parents=True)
    d2 = DESIGN / "D2-schema-and-guidelines.md"
    (out / "guideline.md").write_text(
        "<!-- Verbatim: docs/design/D2-schema-and-guidelines.md §10 (guideline v0) -->\n\n"
        + section(d2, "## 10. Guideline v0 (statistics)", "## 11. Open questions"))
    (out / "model.md").write_text(
        "<!-- Verbatim: docs/design/D1-knowledge-representation.md §1–§11 (§12 and §13 omitted) -->\n\n"
        + section(DESIGN / "D1-knowledge-representation.md", "## 1. Scope and design goals", "## 12. Worked example"))
    schema = ("# core schema v0 (D2 §6), verbatim\n" + (CODE / "schema" / "core.yaml").read_text()
              + "\n---\n# statistics schema v0 (D2 §9), verbatim\n" + (CODE / "schema" / "statistics.yaml").read_text())
    (out / "schema.yaml").write_text(schema)
    d2_73 = re.search(r"```text\n(ClaimProposalBatch.*?)```", section(d2, "### 7.3", "### 7.4"), re.S).group(1)
    (out / "format.md").write_text(FORMAT.replace("{D2_7_3}", d2_73.rstrip()))
    titles = {p: json.loads((S1 / "renditions.json").read_text())[p]["title"] for p in
              {m["page"] for m in SAMPLE["units"].values()}}
    for uid, meta in SAMPLE["units"].items():
        (out / "units" / f"{uid}.md").write_text(unit_packet(uid, meta, titles[meta["page"]]))
    if mode == "golden":
        (out / "pages").mkdir()
        for page in titles:
            here = {u: m for u, m in SAMPLE["units"].items() if m["page"] == page}
            (out / "pages" / f"{name_of(page)}.md").write_text(page_text(page, here))
    for pas in ({"golden": ["a", "b"], "packet_only": ["p"], "offset": ["a"]}[mode]):
        o = f"results/s0/pass_{pas}"
        (out / f"instructions_{pas}.md").write_text(INSTRUCTIONS.format(
            PASS=pas.upper(), OUT=o, UNITS=", ".join(SAMPLE["units"]),
            PAGES_LINE=" and `pages/<page>.md` (the unit's whole page, for context: read the page, "
                       "annotate only the unit, guideline §10.2)." if mode == "golden" else ".",
            VALIDATE=f"cd /home/paul/corpus-structure/docs/design_review/evidence/2026-10-28_design-spikes && "
                     f"UV_PROJECT_ENVIRONMENT=/home/paul/corpus-structure/build/spike-venv uv run python "
                     f"code/s0_check.py {o}"))
    if mode == "offset":
        write_offset_probe(out, titles)
    print("wrote", out)
    return 0


OFFSET_NOTE = """# Offset-form probe: how to cite evidence

This probe differs from the main passes in one respect: cite evidence by **character offsets**,
not by quote. Each `units/<unit>.md` gives the unit's exact text between the two marker lines.
Offsets count Unicode code points from 0 at the first character after the opening marker line;
`end` is exclusive. In your batch, each evidence item is `{"start": int, "end": int, "role": …}`,
statement anchors are `"unit"`, and `unsupported` items carry `start`/`end` instead of
`sentence`/`quote`. Everything else follows `format.md`.
"""


def write_offset_probe(out: Path, titles: dict) -> None:
    for f in (out / "units").glob("*.md"):
        f.unlink()
    for uid in ("T1", "T2", "T3", "T4"):
        meta = SAMPLE["units"][uid]
        text, _, _ = load(meta["page"])
        a, e = meta["parts"][0]["start"], meta["parts"][-1]["end"]
        (out / "units" / f"{uid}.md").write_text(
            f"# Unit {uid} · {titles[meta['page']]}\n\n<<<TEXT BEGINS>>>\n{text[a:e]}\n<<<TEXT ENDS>>>\n"
            f"\n<!-- base offset {a} in rendition {meta['rendition_key']} -->\n")
    (out / "offsets.md").write_text(OFFSET_NOTE)
    (out / "instructions_o.md").write_text(INSTRUCTIONS.format(
        PASS="O (offset probe)", OUT="results/s0/offset_probe", UNITS="T1, T2, T3, T4",
        PAGES_LINE=". Read `offsets.md` first: this pass cites evidence by offsets.",
        VALIDATE="(no validator for this probe: check your offsets by counting carefully)")
        .replace("For each of the twelve units", "For each of the four units")
        .replace("When all twelve are done", "When all four are done"))
    for f in out.glob("instructions_[ab].md"):
        f.unlink()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "golden"))
