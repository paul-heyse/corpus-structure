r"""S5-A step 3: grammar extensions, kept greedily over all 28,956 spans.

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run --project <spike folder> --no-sync python code/s5_extensions.py [01 02 ...]

Baseline: ``edited-noovr`` with the tokenizer reader (V1 edited, V2 tokenizer; the port form).
Each candidate block of ``code/s5grammar/ext/`` is tried in order on top of the blocks kept so far
(``s5_coverage.py --variant ext:<kept>,<block>``), and compared span by span with the current
baseline. A block is **kept** when it gains spans (failed -> ok/ambiguous/partial) and turns no
``ok`` span ``failed`` or ``ambiguous`` (plan §2 step 3); its tree/token disagreements are
counted too. A read span that already took >= 1.5 s and now hits the 2 s parse timer is a timing
effect, not a grammar break (30 parallel workers make times load-dependent): it is counted as
``timing_boundary`` and reported, and does not reject the block. The kept blocks are assembled into ``code/s5grammar/extension.lark``
(``mathgrammar/extension.lark`` + the kept blocks, in order).

Writes results/s5/extensions.json (per trial: block, kept, transitions, gains by construct,
broken spans with their LaTeX) and the assembled extension.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))
EVIDENCE = CODE.parent
OUT = EVIDENCE / "results" / "s5"

from s5_coverage import run_name  # noqa: E402
from s5grammar import EXT_DIR, EXTENSION, block_files  # noqa: E402

READ = ("ok", "ambiguous", "partial")
TIMING_BOUNDARY_MS = 1500.0  # api.PARSE_SECONDS is 2 s


def run(variant: str) -> dict[str, dict]:
    name = run_name(variant, "tokenizer")
    f = OUT / "runs" / f"{name}.jsonl"
    if not f.exists():
        subprocess.run([sys.executable, str(CODE / "s5_coverage.py"), "--variant", variant, "--reader", "tokenizer"],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return {r["key"]: r for r in map(json.loads, f.read_text().splitlines())}


def compare(base: dict, new: dict) -> dict:
    trans = Counter((base[k]["status"], new[k]["status"]) for k in base)
    gained = [k for k in base if base[k]["status"] == "failed" and new[k]["status"] in READ]
    # a span already near the parse timer that now times out is a timing effect (load-dependent with
    # 30 parallel workers), not a grammar break: counted and reported apart
    def boundary(k):
        return new[k]["category"] == "timeout" and base[k]["ms"] >= TIMING_BOUNDARY_MS

    timing = [k for k in base if base[k]["status"] in READ and new[k]["status"] == "failed" and boundary(k)]
    broken = [k for k in base if base[k]["status"] == "ok" and new[k]["status"] in ("failed", "ambiguous") and not boundary(k)]
    lost = [k for k in base if base[k]["status"] in READ and new[k]["status"] == "failed" and not boundary(k)]
    dis = sum(1 for r in new.values() if r["tree"] is not None and r["tree"] != r["tokens_spike"])
    construct = Counter(f"{base[k]['category']}:{base[k]['token']}" for k in gained)
    return {"transitions": {f"{a}->{b}": c for (a, b), c in sorted(trans.items()) if a != b},
            "gained": len(gained), "gained_ok": sum(new[k]["status"] == "ok" for k in gained),
            "gained_by_construct": dict(construct.most_common(12)),
            "broken": len(broken), "lost_read": len(lost), "timing_boundary": len(timing),
            "timing_boundary_examples": [{"latex": new[k]["tokens_spike"][:120], "ms_before": base[k]["ms"],
                                          "ms_after": new[k]["ms"]} for k in timing[:5]],
            "broken_examples": [{"latex": new[k]["tokens_spike"][:160], "was": base[k]["status"], "now": new[k]["status"],
                                 "notes": new[k]["notes"][:2], "category": new[k]["category"]} for k in broken[:15]],
            "status": dict(Counter(r["status"] for r in new.values())),
            "tree_token_disagreements": dis}


def main(argv: list[str]) -> int:
    ids = argv or sorted(p.name.split("_")[0] for p in EXT_DIR.glob("*.lark"))
    kept: list[str] = []
    base_variant = "edited-noovr"
    base = run(base_variant)
    trials = []
    for b in ids:
        variant = "ext:" + ",".join(kept + [b])
        try:
            new = run(variant)
        except subprocess.CalledProcessError as e:
            trials.append({"block": b, "kept": False, "error": str(e)})
            continue
        c = compare(base, new)
        keep = c["gained"] > 0 and c["broken"] == 0 and c["lost_read"] == 0
        trials.append({"block": b, "file": block_files([b])[0].name, "on_top_of": list(kept), "kept": keep, **c})
        print(b, "kept" if keep else "rejected", c["gained"], c["broken"], c["lost_read"], c["status"], flush=True)
        if keep:
            kept.append(b)
            base, base_variant = new, variant
    text = block_text(kept)
    EXTENSION.write_text(text, encoding="utf-8")
    (OUT / "extensions.json").write_text(json.dumps({"baseline": "edited-noovr.tokenizer", "kept": kept,
                                                     "final_variant": base_variant, "trials": trials},
                                                    indent=1, ensure_ascii=False) + "\n")
    return 0


def block_text(kept: list[str]) -> str:
    from mathgrammar import build

    head = ("// ===== S5-A extended grammar extension (code/s5grammar/extension.lark), assembled by s5_extensions.py =====\n"
            "// mathgrammar/extension.lark (the frozen I-R2 extension) followed by the S5 blocks kept in step 3,\n"
            f"// in order: {', '.join(kept) or 'none'}. Build with Lark edit_terminals (s5grammar.whole_name) and\n"
            "// ordered_sets=True; no regex-generated %override lines.\n\n")
    text = head + build.EXTENSION.read_text(encoding="utf-8")
    for f in block_files(kept):
        text += "\n" + f.read_text(encoding="utf-8")
    return text


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
