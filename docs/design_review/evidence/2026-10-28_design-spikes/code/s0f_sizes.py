"""S0-F: batch and packet sizes per unit and pass (S0 plan §7; OPEN-D4-4, D8 work packets).

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/s0f_sizes.py

Per unit: unit text and golden-mode / packet-only packet sizes (input side); per unit and pass
(A, B, P, H, reference): the model-facing batch's characters, Qwen3.5-9B tokens (the cached
tokenizer recorded in results/environment.json), characters ÷ 4, and counts of entities, claims,
unsupported items and alternatives. Writes results/s0/size.tsv and prints a summary.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from tokenizers import Tokenizer

CODE = Path(__file__).resolve().parent
EVIDENCE = CODE.parent
S0 = EVIDENCE / "results" / "s0"
SAMPLE = json.loads((EVIDENCE / "sample.json").read_text())
ENV = json.loads((EVIDENCE / "results" / "environment.json").read_text())
QWEN = Tokenizer.from_file(ENV["tokenizers"]["qwen"]["tokenizer_json"]) if "qwen" in ENV["tokenizers"] else \
    Tokenizer.from_file(next(v["tokenizer_json"] for k, v in ENV["tokenizers"].items() if "qwen" in k.lower()))
PASSES = {"A": S0 / "pass_a", "B": S0 / "pass_b", "P": S0 / "pass_p", "H": S0 / "pass_h", "ref": S0 / "reference_model"}
CAP_LOCAL = 3000  # D4 §4.1 local packet cap (tokens)


def tok(s: str) -> int:
    return len(QWEN.encode(s).ids)


def unit_text(unit: str) -> str:
    meta = SAMPLE["units"][unit]
    text = (EVIDENCE / "results" / "s1" / "canonical" / (meta["page"].replace("/", "__").removesuffix(".html") + ".txt")).read_text()
    return "\n\n".join(text[p["start"]:p["end"]] for p in meta["parts"])


def main() -> int:
    rows = []
    for u in SAMPLE["units"]:
        ut = unit_text(u)
        gp = (S0 / "inputs" / "golden" / "units" / f"{u}.md").read_text()
        pp = (S0 / "inputs" / "packet_only" / "units" / f"{u}.md").read_text()
        base = {"unit": u, "unit_chars": len(ut), "unit_tokens": tok(ut), "golden_packet_tokens": tok(gp),
                "packet_only_tokens": tok(pp)}
        for name, d in PASSES.items():
            f = d / f"{u}.json"
            if not f.exists():
                continue
            raw = f.read_text()
            b = json.loads(raw)
            compact = json.dumps(b, ensure_ascii=False, separators=(",", ":"))
            rows.append({**base, "pass": name, "batch_chars": len(compact), "batch_tokens": tok(compact),
                         "batch_chars_div4": len(compact) // 4, "entities": len(b.get("entities", [])),
                         "claims": len(b.get("claims", [])), "unsupported": len(b.get("unsupported", [])),
                         "alternatives": len(b.get("alternatives", []))})
    out = S0 / "size.tsv"
    with out.open("w", encoding="utf-8") as fh:
        fh.write("\t".join(rows[0]) + "\n")
        for r in rows:
            fh.write("\t".join(str(v) for v in r.values()) + "\n")
    ref = [r for r in rows if r["pass"] == "ref"]
    bt = sorted(r["batch_tokens"] for r in rows)
    print("units", len(ref), "| unit tokens max", max(r["unit_tokens"] for r in ref),
          "| golden packet tokens max", max(r["golden_packet_tokens"] for r in ref),
          "| packet-only tokens max", max(r["packet_only_tokens"] for r in ref))
    print("batch tokens (all passes): median", bt[len(bt) // 2], "max", bt[-1],
          "| packet + batch over the local cap", sum(1 for r in rows if r["packet_only_tokens"] + r["batch_tokens"] > CAP_LOCAL))
    print("tokens per character, batches:", round(sum(r["batch_tokens"] for r in rows) / sum(r["batch_chars"] for r in rows), 3))
    for r in ref:
        print(f"  {r['unit']:4s} unit {r['unit_tokens']:4d}  packet {r['packet_only_tokens']:4d}  ref batch {r['batch_tokens']:5d}  claims {r['claims']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
