"""I-R2: the token form (D1 §6.2) over every math span of the four spike pages.

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/i_r2_token_form.py

Writes results/i_r2/:
- token_form_spike_pages.jsonl: one row per math span of the S1 renditions (results/s1/),
  {page, start, end, latex, macros, token_form}: ``latex`` is the canonical-text slice with its
  delimiters, ``macros`` the effective macro table used (page macros over the D2 §12.1 fallback,
  ``instruments.values.merged_macros``), ``token_form`` the key form. The parity file for the
  product's ``core/tex.py`` (P0-F-2a), which must reproduce every row.
- tree_token_property.tsv: the corpus layer of the tree/token property: for every span, the parse
  status under ``any_value``, the tree printer's form, the token form, and the cause of each
  disagreement.
- summary.json: counts, and the macro tokens left unexpanded at the depth bound.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))

import mathgrammar as M  # noqa: E402
from mathgrammar.printer import SIZING_COMMANDS, TEXT_MODE, tex_tokens  # noqa: E402
from instruments.values import merged_macros  # noqa: E402

EVIDENCE = CODE.parent
S1 = EVIDENCE / "results" / "s1"
OUT = EVIDENCE / "results" / "i_r2"
PAGES = ["special/LocationScale.html", "special/Normal.html", "special/LogNormal.html", "special/Gamma.html"]


def _stem(page: str) -> str:
    return page.replace("/", "__").removesuffix(".html")


def cause(latex: str, tree: str, tok: str) -> str:
    """Why the tree printer and the token form differ (the corpus layer lists every cause)."""
    toks = set(tex_tokens(latex))
    if toks & set(SIZING_COMMANDS):
        return "sizing command"
    if toks & TEXT_MODE and re.sub(r"\s", "", tok) == re.sub(r"\s", "", tree):
        return "text-mode whitespace (the grammar ignores whitespace; the token form keeps one space)"
    if toks & {"\\left", "\\right"} and any(t.startswith(("\\left", "\\right")) and t not in ("\\left", "\\right") for t in toks):
        return "\\left/\\right prefix of a longer command"
    return "other"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    renditions = json.loads((S1 / "renditions.json").read_text())
    rows, prop, unexpanded = [], [], []
    for page in PAGES:
        text = (S1 / "canonical" / f"{_stem(page)}.txt").read_text(encoding="utf-8")
        segs = [json.loads(x) for x in (S1 / "segments" / f"{_stem(page)}.jsonl").read_text().splitlines() if x.strip()]
        eff = merged_macros(renditions[page]["parse_detail"]["macros"])
        table = M.macro_table(eff)
        macros = {k: eff[k] for k in sorted(eff)}
        for s in segs:
            if not s["kind"].startswith("math"):
                continue
            latex = text[s["start"]:s["end"]]
            form, unexp = M.token_form(latex, table)
            if unexp:
                unexpanded.append({"page": page, "start": s["start"], "tokens": unexp})
            rows.append({"page": page, "start": s["start"], "end": s["end"], "latex": latex, "macros": macros,
                         "token_form": form})
            r = M.parse(latex, "any_value", macros=eff)
            agr = M.tree_token_agreement(r)
            assert agr["token"] == form
            prop.append({"page": page, "start": s["start"], "end": s["end"], "kind": s["kind"], "status": r.status,
                         "agree": agr["agree"], "cause": "" if agr["agree"] in (True, None) else cause(latex, agr["tree"], form),
                         "token_form": form, "tree_form": agr["tree"] or "", "latex": latex})
    with (OUT / "token_form_spike_pages.jsonl").open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=False) + "\n")
    with (OUT / "tree_token_property.tsv").open("w", encoding="utf-8") as fh:
        fh.write("\t".join(prop[0]) + "\n")
        for r in prop:
            fh.write("\t".join(str(v).replace("\t", " ").replace("\n", " ") for v in r.values()) + "\n")
    parsed = [r for r in prop if r["agree"] is not None]
    summary = {
        "spans": len(rows),
        "spans_by_page": dict(Counter(r["page"] for r in rows)),
        "parsed": len(parsed),
        "status": dict(Counter(r["status"] for r in prop)),
        "tree_token_agree": sum(1 for r in parsed if r["agree"]),
        "tree_token_differ": sum(1 for r in parsed if not r["agree"]),
        "differ_by_cause": dict(Counter(r["cause"] for r in parsed if not r["agree"])),
        "spans_with_sizing_commands": sum(1 for r in rows if set(tex_tokens(r["latex"])) & set(SIZING_COMMANDS)),
        "spans_with_text_mode_whitespace": sum(1 for r in rows if re.search(r"\\(?:text|mathrm|textrm|mbox|operatorname)\s*\{[^}]*\s[^}]*\}", r["latex"])),
        "unexpanded_at_depth_bound": unexpanded,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "unexpanded_at_depth_bound"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
