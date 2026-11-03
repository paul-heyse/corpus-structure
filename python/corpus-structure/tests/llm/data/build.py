"""Write the thin spike fixtures of `tests/llm` once, from the frozen spike results (stdlib only;
run from the repository root: `python3 python/corpus-structure/tests/llm/data/build.py`).

It reads the spike's results as data and imports no spike code.

- `units.json`: per spike unit, its page and its packet's sentence ids with their offsets on the
  frozen S1 rendition: the S0 units from the spike's `sample.json`, the S0-R2 units (the held-out
  and example ones, and the core units' standing context `cN`) from `results/s0r2/sample.json`.
- `quotes.json`: every quote the spike located for the S0 batch sets (record `s0.stored`: passes
  A, B, P and H, the D7 adjudication, the trace batches, the reference) and the S0-R2 sets (passes
  HV and SV, the v1 adjudication): its path, quote, cited sentence id, stored offsets and the step
  that found it, from each set's `report.json`.
- `reference_v1.json`: the stored v1 reference (`results/s0r2/reference_v1`) as segment extents,
  for the anchors-by-locator comparison with `fixtures/s0`: statement anchors, local entities'
  scope segments and scope qualifiers' segments as `[kind, start, end]`, claims' evidence spans,
  unsupported spans and every phrase span under a claim, in the stored JSON's order.
- `perturbations.json`: the text-math note's L-10 set (`p6_quote_tokens.py` over
  `code/regex_probe.py` part A): the distinct (unit, sentence, quote) of passes A, B, P, H and the
  reference that the spike located exactly, perturbed with the same kinds, order and seed
  (20261028), each with its ground-truth span, the unperturbed quote's stored offsets.

The committed JSON is the fixture's authority; this script is provenance. These are frozen
historical inputs to current component checks, not qualification of today's PDF recognition or
provider. Changes must cite the original paths/records above, state the intended semantic or
coordinate difference, adjudicate independently under the cited source and D1 §6.2, and add a new
explicitly selected reference while preserving the old witness. A current producer rerun supplies
a candidate difference, not authority to accept it.
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path

REPO = Path.cwd()
EVIDENCE = REPO / "docs/design_review/evidence/2026-10-28_design-spikes"
RESULTS = EVIDENCE / "results"
OUT = Path(__file__).resolve().parent
S0_SETS = {
    "pass_a": "s0/stored/pass_a",
    "pass_b": "s0/stored/pass_b",
    "pass_p": "s0/stored/pass_p",
    "pass_h": "s0/stored/pass_h",
    "adjudication_d7": "s0/stored/adjudication_d7",
    "trace": "s0/trace_stored",
    "reference": "s0/reference",
}
S0R2_SETS = {
    "pass_hv": "s0r2/stored/pass_hv",
    "pass_sv": "s0r2/stored/pass_sv",
    "adjudication_v1": "s0r2/stored/adjudication_v1",
}
PROBE_SETS = {
    "pass_a": "pass_a",
    "pass_b": "pass_b",
    "pass_p": "pass_p",
    "pass_h": "pass_h",
    "reference": "reference_model",
}
STEP = {"exact_sentence": "exact_cited", "exact_unit": "exact_frame", "spacing": "spacing"}


def jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def units() -> dict:
    out: dict = {"s0": {}, "s0r2": {}}
    for name, path in (("s0", EVIDENCE / "sample.json"), ("s0r2", RESULTS / "s0r2/sample.json")):
        for uid, unit in json.loads(path.read_text())["units"].items():
            sentences = {
                s["id"]: [s["start"], s["end"]] for p in unit["parts"] for s in p["sentences"]
            }
            for c in unit.get("context", []):
                sentences[c["id"]] = [c["start"], c["end"]]
            out[name][uid] = {
                "page": unit["page"],
                "parts": [[p["kind"], p["start"], p["end"]] for p in unit["parts"]],
                "sentences": sentences,
            }
    return out


def quotes() -> dict:
    out: dict = {}
    for family, sets in (("s0", S0_SETS), ("s0r2", S0R2_SETS)):
        for name, folder in sets.items():
            report = json.loads((RESULTS / folder / "report.json").read_text())
            rows = []
            for uid, entry in sorted(report.items()):
                for r in entry["locate"]["records"]:
                    rows.append(
                        [
                            uid,
                            r["loc"],
                            r["quote"],
                            r["sentence"],
                            r["start"],
                            r["end"],
                            STEP.get(r["step"], r["step"]),
                        ]
                    )
            out[name] = {"units": family, "source": f"results/{folder}/report.json", "quotes": rows}
    return out


def segment_extents(folder: str, page: str) -> dict[str, list]:
    stem = page.replace("/", "__").removesuffix(".html")
    rows = jsonl(EVIDENCE / folder / "segments" / f"{stem}.jsonl")
    rows += jsonl(EVIDENCE / folder / "sentences" / f"{stem}.provisional.jsonl")
    return {r["key"]: [r["kind"], r["start"], r["end"]] for r in rows}


def spans_under(node: object) -> list[list[int]]:
    found: list[list[int]] = []
    if isinstance(node, dict):
        if isinstance(node.get("start"), int) and isinstance(node.get("end"), int):
            found.append([node["start"], node["end"]])
        for v in node.values():
            found += spans_under(v)
    elif isinstance(node, list):
        for v in node:
            found += spans_under(v)
    return found


def reference_v1() -> dict:
    out = {}
    for path in sorted((RESULTS / "s0r2/reference_v1").glob("[TU]*.json")):
        stored = json.loads(path.read_text())
        page = json.loads((RESULTS / "s0r2/sample.json").read_text())["units"][path.stem]["page"]
        ext = segment_extents("results/s1", page)
        claims = {}
        for c in stored["claims"]:
            scope = (c.get("qualifiers") or {}).get("scope")
            claims[c["local_ref"]] = {
                "evidence": [[e["start"], e["end"], e["role"]] for e in c["evidence"]],
                "phrases": spans_under({"object": c.get("object"), "q": c.get("qualifiers")}),
                "scope": ext[scope["segment"]] if isinstance(scope, dict) else None,
            }
        out[path.stem] = {
            "page": page,
            "statements": {
                s["local_ref"]: [ext[k] for k in s["anchor"]] for s in stored["statements"]
            },
            "entities": {
                e["local_ref"]: ext[e["scope_segment"]]
                for e in stored["entities"]
                if e.get("scope") == "local"
            },
            "claims": claims,
            "unsupported": {
                u["local_ref"]: [u["start"], u["end"]] for u in stored.get("unsupported", [])
            },
        }
    return out


# --- L-10 perturbations (as code/regex_probe.py `perturb`, same seed and order) ------------------


def perturb(q: str, kind: str, rng: random.Random) -> str | None:
    words = q.split(" ")
    if kind == "respace":
        if "\\(" not in q and "\\[" not in q:
            return None
        return (
            re.sub(r"\s*([=+\-<>,])\s*", r" \1 ", q).replace("\\( ", "\\(").replace(" \\)", "\\)")
        )
    if kind == "typo":
        idx = [i for i, c in enumerate(q) if c.isalpha() and (i == 0 or q[i - 1] != "\\")]
        if len(idx) < 8:
            return None
        i = rng.choice(idx[2:-2])
        return q[:i] + ("e" if q[i] != "e" else "a") + q[i + 1 :]
    if kind == "drop_word":
        cand = [
            i for i, w in enumerate(words) if len(w) >= 3 and w.isalpha() and 0 < i < len(words) - 1
        ]
        if len(words) < 6 or not cand:
            return None
        i = rng.choice(cand)
        return " ".join(words[:i] + words[i + 1 :])
    if kind == "trim_end":
        return q[:-2] if len(q) > 20 and q[-2].isalnum() else None
    if kind == "add_period":
        return q + "." if not q.endswith(".") else None
    if kind == "macro":
        return q.replace("\\R", "\\mathbb{R}") if "\\R" in q else None
    raise ValueError(kind)


def authored_quotes() -> list[tuple[str, str, str]]:
    found: set[tuple[str, str, str]] = set()
    for folder in PROBE_SETS.values():
        for path in (RESULTS / "s0" / folder).glob("[TU]*.json"):

            def walk(o: object, unit: str = path.stem) -> None:
                if isinstance(o, dict):
                    if isinstance(o.get("quote"), str) and isinstance(o.get("sentence"), str):
                        found.add((unit, o["sentence"], o["quote"]))
                    for v in o.values():
                        walk(v)
                elif isinstance(o, list):
                    for v in o:
                        walk(v)

            walk(json.loads(path.read_text()))
    return sorted(found)


def perturbations(unit_map: dict, quote_sets: dict) -> dict:
    truth: dict[tuple[str, str, str], tuple[int, int, str]] = {}
    for name in PROBE_SETS:
        for uid, _loc, quote, sentence, start, end, step in quote_sets[name]["quotes"]:
            truth.setdefault((uid, sentence, quote), (start, end, step))
    rng = random.Random(20261028)
    kinds = ["respace", "typo", "drop_word", "trim_end", "add_period", "macro"]
    rows = []
    for uid, sentence, quote in authored_quotes():
        gt = truth.get((uid, sentence, quote))
        if gt is None or gt[2] not in ("exact_cited", "exact_frame"):
            continue
        if sentence not in unit_map["s0"][uid]["sentences"]:
            continue
        for kind in kinds:
            changed = perturb(quote, kind, rng)
            if changed is None or changed == quote:
                continue
            rows.append([uid, sentence, kind, quote, changed, gt[0], gt[1]])
    return {
        "seed": 20261028,
        "source": "p6_quote_tokens.py over code/regex_probe.py part A",
        "rows": rows,
    }


def main() -> None:
    unit_map = units()
    quote_sets = quotes()
    data = {
        "units": unit_map,
        "quotes": quote_sets,
        "reference_v1": reference_v1(),
        "perturbations": perturbations(unit_map, quote_sets),
    }
    for name, value in data.items():
        text = json.dumps(value, ensure_ascii=False, indent=None, separators=(",", ":"))
        (OUT / f"{name}.json").write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
