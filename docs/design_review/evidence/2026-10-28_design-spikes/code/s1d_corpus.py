"""S1-D: the 78 first-pass pages under the adopted configuration, plus corpus-wide V1, V2, V5, V6.

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/s1d_corpus.py

Writes results/s1/{counts,parser_diff,coverage,dfn_terms,macros,links,sizes,repairs,v6_corpus}.tsv|json
and results/s1/corpus_summary.json. Plan: S1 document §8 and §5.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from s1_adapter import CORPUS, EVIDENCE, REPO, adapt  # noqa: E402
from s1a_variants import blocks, structure, v6_walker  # noqa: E402
from s1b_sample import independent_text, structural  # noqa: E402
from tokenizers import Tokenizer  # noqa: E402

OUT = EVIDENCE / "results" / "s1"
INDEX = REPO / "docs/statistics_corpus/index"
ENV = json.loads((EVIDENCE / "results" / "environment.json").read_text())
TOK = {k: Tokenizer.from_file(v["tokenizer_json"]) for k, v in ENV["tokenizers"].items()}


def first_pass() -> list[dict]:
    with (INDEX / "siegrist_sections.tsv").open() as f:
        return [r for r in csv.DictReader(f, delimiter="\t") if r["first_pass"] == "yes"]


def write_tsv(name: str, rows: list[dict]) -> None:
    if not rows:
        return
    with (OUT / name).open("w", newline="", encoding="utf-8") as f:
        fields = list(dict.fromkeys(k for r in rows for k in r))
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t", restval=0)
        w.writeheader()
        w.writerows(rows)


def math_share(text: str, segs: list[dict], start: int, end: int) -> float:
    inside = sum(min(s["end"], end) - max(s["start"], start) for s in segs
                 if s["kind"].startswith("math") and s["start"] < end and s["end"] > start)
    return inside / max(1, end - start)


def main() -> int:
    index = first_pass()
    terms_index: dict[str, list[str]] = defaultdict(list)
    with (INDEX / "siegrist_defined_terms.tsv").open() as f:
        for r in csv.DictReader(f, delimiter="\t"):
            terms_index[r["path"]].append(re.sub(r"\s+", " ", r["term"]).strip())
    counts, pdiff, coverage, dfn_rows, links, sizes, repairs = [], [], [], [], [], [], []
    macro_sets: dict[str, list[str]] = defaultdict(list)
    v6_default = Counter()
    v6_safe = Counter()
    v6_examples: list[dict] = []
    invariant_totals = Counter()
    statuses = Counter()
    anomalies: list[dict] = []
    nfkc_changed: list[dict] = []
    engines_all_identical = True
    for row in index:
        page = row["path"]
        r = adapt(page)
        segs, text = r["segments"], r["text"]
        kinds = Counter(s["kind"] for s in segs)
        units = [s for s in segs if s["kind"] == "unit"]
        defs = [u for u in units if u["attrs"].get("hint", {}).get("statement_kind") == "definition"]
        defs_dfn_only = [u for u in units if u["attrs"].get("hint", {}).get("selector") == "p.dfn"]
        dfn = [m for m in r["markup"] if m["markup"] == "dfn"]
        disp = [s for s in segs if s["kind"] == "math_display"]
        disp_bracket = [s for s in disp if s["attrs"].get("open") == "\\["]
        ours = {"units": len(units), "definition_units": len(defs_dfn_only), "dfn_terms": len(dfn),
                "details_blocks": kinds["details"], "display_math": len(disp_bracket)}
        rec = {"page": page}
        for k, v in ours.items():
            rec[f"{k}_ours"] = v
            rec[f"{k}_index"] = int(row[k])
            rec[f"{k}_delta"] = v - int(row[k])
        rec["definition_units_incl_dfm_dfin"] = len(defs)
        rec["display_math_incl_align"] = len(disp)
        counts.append(rec)
        # dfn terms item by item
        ours_terms = Counter(re.sub(r"\s+", " ", m["text"]).strip() for m in dfn)
        idx_terms = Counter(terms_index.get(page, []))
        for t in sorted(set(ours_terms) | set(idx_terms)):
            if ours_terms[t] != idx_terms[t]:
                dfn_rows.append({"page": page, "term": t, "ours": ours_terms[t], "index": idx_terms[t]})
        # invariants
        st = structural(r)
        for k, v in st.items():
            invariant_totals[k] += v["count"]
        it = independent_text(page, r)
        invariant_totals["independent_checked"] += it["checked"]
        invariant_totals["independent_mismatched"] += it["mismatched"]
        for s in segs:
            if s["kind"].startswith("math"):
                statuses[s["parse_status"]] += 1
                if s["parse_status"] != "ok":
                    anomalies.append({"page": page, "segment": s["key"], "reason": s.get("reason"),
                                      "text": text[s["start"]:s["end"]][:100]})
        for a in r["rendition"]["parse_detail"]["math_anomalies"]:
            anomalies.append({"page": page, "anomaly": a})
        for o in r["rendition"]["parse_detail"]["orphans"]:
            repairs.append({"page": page, "parser": "lxml", "container": o["container"],
                            "sourceline": o["sourceline"], "text": o["text"]})
        # profile engines and coverage
        eng = r["rendition"]["profile_engines"]
        engines_all_identical &= eng["all_identical"]
        coverage.append({"page": page, "engines_identical": eng["all_identical"],
                         "role_conflicts": len(eng["role_conflicts"]),
                         "excluded_elements": len(r["exclusions"]),
                         **{f"excl_{k}": v for k, v in Counter(e["rule"] for e in r["exclusions"]).items()},
                         "division_segments": kinds["division"], "figure_segments": kinds["figure"]})
        # V1 parser, V2 normalization
        h5 = adapt(page, {"parser": "html5lib"})
        a, b = structure(r), structure(h5)
        sa, sb = set(a), set(b)
        pdiff.append({"page": page, "only_lxml": sum(1 for x in a if x not in sb),
                      "only_html5lib": sum(1 for x in b if x not in sa),
                      "chars_lxml": len(text), "chars_html5lib": len(h5["text"]),
                      "orphans_lxml": len(r["rendition"]["parse_detail"]["orphans"]),
                      "orphans_html5lib": len(h5["rendition"]["parse_detail"]["orphans"]),
                      "example_lxml": next((t[:100] for k, t in a if (k, t) not in sb and k != "document"), ""),
                      "example_html5lib": next((t[:100] for k, t in b if (k, t) not in sa and k != "document"), "")})
        for o in h5["rendition"]["parse_detail"]["orphans"]:
            repairs.append({"page": page, "parser": "html5lib", "container": o["container"],
                            "sourceline": o["sourceline"], "text": o["text"]})
        nk = adapt(page, {"unicode": "NFKC"})
        for u in nk["rendition"]["parse_detail"]["unicode_changed"]:
            nfkc_changed.append({"page": page, **u})
        # V6
        bl = blocks(r)
        d, s_ = v6_walker(bl, prose_safe=False), v6_walker(bl, prose_safe=True)
        for k in ("spans_agree", "scanner_only", "walker_only", "comment_nodes", "parse_errors"):
            v6_default[k] += d[k]
            v6_safe[k] += s_[k]
        v6_examples += [{"page": page, "state": "default", **e} for e in d["examples"][:3]]
        v6_examples += [{"page": page, "state": "prose_safe", **e} for e in s_["examples"][:3]]
        # macros
        for name, m in r["rendition"]["parse_detail"]["macros"].items():
            macro_sets[f"{name} -> {m['body']} ({m['nargs']})"].append(page)
        # links
        for m in r["markup"]:
            if m["markup"] == "a":
                href = m.get("href") or ""
                kind = ("ancillary" if "openAncillary" in href else "external" if href.startswith("http")
                        else "same_page_anchor" if href.startswith("#") else "internal")
                links.append({"page": page, "kind": kind, "href": href[:120], "text": m["text"][:60]})
        # sizes: units and paragraphs outside units
        by_key = {s["key"]: s for s in segs}
        for s in segs:
            if s["kind"] == "unit" or (s["kind"] == "paragraph" and not any(
                    by_key.get(p, {}).get("kind") == "unit" for p in _ancestors(s, by_key))):
                t = text[s["start"]:s["end"]]
                sizes.append({"page": page, "kind": s["kind"], "segment": s["key"], "chars": len(t),
                              "words": len(t.split()), "math_share": round(math_share(t, segs, s["start"], s["end"]), 3),
                              "qwen_tokens": len(TOK["qwen3.5-9b"].encode(t).ids),
                              "gliner_tokens": len(TOK["gliner2.5-base-v1"].encode(t).ids),
                              "hint": s["attrs"].get("hint", {}).get("statement_kind", "")})
        print(page, "ok", flush=True)
    write_tsv("counts.tsv", counts)
    write_tsv("parser_diff.tsv", pdiff)
    write_tsv("coverage.tsv", coverage)
    write_tsv("dfn_terms.tsv", dfn_rows)
    write_tsv("links.tsv", links)
    write_tsv("sizes.tsv", sizes)
    write_tsv("repairs.tsv", repairs)
    macro_rows = [{"definition": k, "pages": len(v), "example_pages": ";".join(v[:3])} for k, v in
                  sorted(macro_sets.items(), key=lambda kv: -len(kv[1]))]
    write_tsv("macros.tsv", macro_rows)
    summary = {
        "pages": len(index), "invariants": dict(invariant_totals), "math_parse_status": dict(statuses),
        "math_anomalies": anomalies, "nfkc_changed": nfkc_changed[:50], "nfkc_changed_count": len(nfkc_changed),
        "profile_engines_identical_all_pages": engines_all_identical,
        "v6": {"default_state": dict(v6_default), "prose_safe": dict(v6_safe), "examples": v6_examples[:40]},
        "pages_with_count_delta": {k: sum(1 for c in counts if c[f"{k}_delta"] != 0) for k in
                                   ("units", "definition_units", "dfn_terms", "details_blocks", "display_math")},
    }
    (OUT / "corpus_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: summary[k] for k in ("invariants", "math_parse_status", "profile_engines_identical_all_pages",
                                               "pages_with_count_delta", "nfkc_changed_count")}, indent=1))
    print(json.dumps(summary["v6"]["default_state"]), json.dumps(summary["v6"]["prose_safe"]))
    return 0


def _ancestors(s: dict, by_key: dict) -> list[str]:
    out = []
    while s.get("parent"):
        out.append(s["parent"])
        s = by_key[s["parent"]]
    return out


if __name__ == "__main__":
    sys.exit(main())
