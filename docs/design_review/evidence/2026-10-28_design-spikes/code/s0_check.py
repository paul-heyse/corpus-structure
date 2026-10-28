"""S0: validate a folder of model-facing batches and convert them to the stored form.

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/s0_check.py FOLDER [--out STORED_DIR]

For each <unit>.json in FOLDER: build the unit context from sample.json and the S1 rendition
(canonical text, sentences, sections, statement anchors), validate the model-facing form
(instruments.validate), locate quotes and convert to the stored form (s0_locate.to_stored), and
validate the stored form against the canonical text. Prints one line per unit; with --out, writes
stored batches and a report.json there. Exit status 1 if any unit has issues.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))
from instruments.validate import validate_batch  # noqa: E402
from s0_locate import UnitContext, to_stored  # noqa: E402

EVIDENCE = CODE.parent
S1 = EVIDENCE / "results" / "s1"
SAMPLE = json.loads((EVIDENCE / "sample.json").read_text())


def _name(page: str) -> str:
    return page.replace("/", "__").removesuffix(".html")


def context(unit: str) -> UnitContext:
    meta = SAMPLE["units"][unit]
    page = meta["page"]
    text = (S1 / "canonical" / f"{_name(page)}.txt").read_text(encoding="utf-8")
    segs = [json.loads(x) for x in (S1 / "segments" / f"{_name(page)}.jsonl").read_text().splitlines()]
    sections = [s for s in segs if s["kind"] == "section"]
    sentences = {s["id"]: (s["start"], s["end"]) for p in meta["parts"] for s in p["sentences"]}
    sentence_keys = {s["id"]: s["key"] for p in meta["parts"] for s in p["sentences"]}
    statement_kinds = {"unit", "paragraph", "details", "list_item"}
    by_key = {s["key"]: s for s in segs}

    def section_of(offset: int) -> str | None:
        inside = [s for s in sections if s["start"] <= offset < s["end"]]
        return min(inside, key=lambda s: s["end"] - s["start"])["key"] if inside else None

    sent_span = {sentence_keys[i]: {"start": a, "end": e} for i, (a, e) in sentences.items()}

    def statement_scope(keys: list[str]) -> str | None:
        spans = [by_key.get(k) or sent_span.get(k) for k in keys]
        spans = [s for s in spans if s]
        if not spans:
            return None
        lo, hi = min(s["start"] for s in spans), max(s["end"] for s in spans)
        cands = [s for s in segs if s["kind"] in statement_kinds and s["start"] <= lo and hi <= s["end"]]
        return min(cands, key=lambda s: s["end"] - s["start"])["key"] if cands else None

    return UnitContext(text=text, unit_ranges=[(p["start"], p["end"]) for p in meta["parts"]],
                       sentences=sentences, unit_keys=[p["segment_key"] for p in meta["parts"]],
                       sentence_keys=sentence_keys, section_of=section_of, statement_scope=statement_scope,
                       document_key=meta["document_key"])


def check(folder: Path, out: Path | None) -> int:
    failures = 0
    report = {}
    for path in sorted(folder.glob("*.json")):
        unit = path.stem
        if unit not in SAMPLE["units"]:
            continue
        raw = json.loads(path.read_text())
        ctx = context(unit)
        model = validate_batch(raw, form="model", sentence_ids=ctx.sentences.keys())
        try:
            stored, loc = to_stored(raw, ctx)
        except Exception as exc:  # reported, never hidden
            print(f"{unit}\tconversion failed: {exc!r}")
            failures += 1
            report[unit] = {"conversion_error": repr(exc), "model_issues": model.lines()}
            continue
        st = validate_batch(stored, form="stored", canonical_text=ctx.text, unit_ranges=ctx.unit_ranges)
        tiers = loc.by_tier()
        bad = (not model.ok) or (not st.ok) or loc.unlocated() or loc.problems
        failures += bool(bad)
        print(f"{unit}\tmodel issues {len(model.issues)}\tstored issues {len(st.issues)}\tquotes {tiers}"
              f"\tambiguous {len(loc.ambiguous())}\tproblems {len(loc.problems)}")
        for line in [*model.lines(), *st.lines(), *loc.problems][:12]:
            print("   ", line)
        report[unit] = {"model_issues": model.lines(), "stored_issues": st.lines(), "locate": loc.as_json()}
        if out:
            out.mkdir(parents=True, exist_ok=True)
            stored = {"envelope": {"unit": unit, "rendition_key": SAMPLE["units"][unit]["rendition_key"],
                                   "source": str(path.resolve().relative_to(EVIDENCE))}, **stored}
            (out / f"{unit}.json").write_text(json.dumps(stored, indent=1, ensure_ascii=False) + "\n")
    if out:
        (out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    return 1 if failures else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    sys.exit(check(a.folder, a.out))
