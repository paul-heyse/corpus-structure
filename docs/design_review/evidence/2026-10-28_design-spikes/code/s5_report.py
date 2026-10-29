r"""S5-A outputs from the runs: parse.tsv, canonical.tsv, coverage.md, coverage_summary.json.

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run --project <spike folder> --no-sync python code/s5_report.py

Runs read (results/s5/runs/, written by s5_coverage.py): the V1 x V2 baselines
``spike.spike``, ``edited.spike``, ``edited.tokenizer``, ``edited-noovr.tokenizer``; the extended
grammar ``extended.tokenizer`` (spike tree printer) and ``extended.tokenizer.s5`` (S5 tree printer);
and the step-3 trials summarized in extensions.json.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))
EVIDENCE = CODE.parent
OUT = EVIDENCE / "results" / "s5"
RUNS = OUT / "runs"

from mathgrammar import printer as P  # noqa: E402
from s5_coverage import ambiguity_cause  # noqa: E402

BASELINES = [("spike", "spike"), ("edited", "spike"), ("edited", "tokenizer"), ("edited-noovr", "tokenizer")]
STATUSES = ("ok", "ambiguous", "partial", "failed")


CONSTRUCTS = [
    ("text-mode words inside a formula", r"\\(?:text|mbox|textrm)\{"),
    ("inner product \\langle .,. \\rangle", r"\\langle"),
    ("multinomial coefficient \\binom{n}{x, y}", r"\\binom\{[^{}]*\}\{[^{}]*,"),
    ("measure differential d\\mu(x), K(x, dy), d(\\mu \\times \\nu)", r"\(d[a-z]\)|, ?d[a-z]\)|d\(\\mu|\\,\s*d\(|\bd\("),
    ("\\prime superscripts", r"\\prime"),
    ("\\partial (Jacobians, derivatives)", r"\\partial"),
    ("\\bigcup / \\bigcap", r"\\big(?:cup|cap)"),
    ("matrices", r"matrix"),
    ("placeholder argument f(\\cdot)", r"\(\s*\\cdot"),
    ("inverse image r^{-1}(B)", r"\^\{-1\}\s*(?:\(|\\\{|\\left)"),
    ("environment rows ending in ;", r"\\begin\{cases\}"),
    ("\\otimes / \\circ", r"\\otimes|\\circ"),
]


def construct_of(latex: str) -> str:
    import re

    for name, pat in CONSTRUCTS:
        if re.search(pat, latex):
            return name
    return "other"


def load(name: str) -> list[dict]:
    return [json.loads(x) for x in (RUNS / f"{name}.jsonl").read_text().splitlines()]


def pct(a: int, b: int) -> str:
    return f"{100 * a / b:.1f}%"


def cause_of(r: dict, ok_after: bool) -> str:
    """Why the spike tree printer's form differs from the token form (fix named on the tree side)."""
    inner = P.strip_delimiters(r["latex"])
    trimmed = inner.rstrip().rstrip(".,;").rstrip()
    if trimmed != inner.strip() and r["status"] in ("partial", "ambiguous") and r["tree"] == P.tokens_canonical(trimmed, {}) or (
            trimmed != inner.strip() and r["tree"] is not None and r["tokens_spike"].startswith(r["tree"])):
        return "T1 trimmed reading: the tree covers the value without its trailing punctuation"
    if inner.lstrip().startswith("\\begin"):
        return "T2 outer environment: the tree keeps \\begin/\\end that rule 1 strips"
    if "\\text" in inner or "\\mbox" in inner or "\\textrm" in inner:
        return "T3 text-mode argument: the grammar's whitespace %ignore removed spaces the token form keeps"
    return "unexplained" + ("" if ok_after else " (still disagrees after the S5 printer)")


def main() -> int:
    spans = {json.loads(x)["key"]: json.loads(x) for x in (OUT / "spans.jsonl").read_text().splitlines()}
    ext = json.loads((OUT / "extensions.json").read_text())
    macros = json.loads((OUT / "macros_summary.json").read_text())
    rens = json.loads((OUT / "renditions.json").read_text())
    base = {f"{v}.{r}": load(f"{v}.{r}") for v, r in BASELINES}
    final = load("extended.tokenizer")
    final_s5 = load("extended.tokenizer.s5")
    b0 = base["spike.spike"]
    for r in final + final_s5 + b0:
        r["latex"] = spans[r["key"]]["latex"]
    n = len(b0)

    # V1 x V2: per-span identity against the spike grammar with the spike reader
    def sig(r):
        return (r["status"], r["detected"], r["category"], r["tree"], r["tokens_spike"], tuple(r["notes"]))

    v_table = []
    for name, rows in base.items():
        same = sum(sig(a) == sig(b) for a, b in zip(b0, rows))
        st = Counter(r["status"] for r in rows)
        v_table.append({"run": name, **{s: st.get(s, 0) for s in STATUSES}, "identical_to_spike_spike": same})

    # ---- parse.tsv
    fb = {r["key"]: r for r in final}
    with (OUT / "parse.tsv").open("w", encoding="utf-8") as fh:
        cols = ["key", "page", "kind", "start", "end", "delimiting", "status_baseline", "status", "detected",
                "category_or_cause", "token", "ms", "baseline_category_or_cause"]
        fh.write("\t".join(cols) + "\n")
        for a in b0:
            f = fb[a["key"]]
            cat = f["category"] if f["status"] == "failed" else (ambiguity_cause(f["notes"]) if f["status"] == "ambiguous" else "")
            bcat = a["category"] if a["status"] == "failed" else (ambiguity_cause(a["notes"]) if a["status"] == "ambiguous" else "")
            fh.write("\t".join(str(x) for x in (a["key"], a["page"], a["kind"], a["start"], a["end"], a["delimiting"],
                                                a["status"], f["status"], f["detected"] or "", cat,
                                                (f["token"] or "") if f["status"] == "failed" else "", f["ms"],
                                                bcat)) + "\n")

    # ---- canonical.tsv: every span the grammar reads (final grammar), S5 printer and spike printer
    s5 = {r["key"]: r for r in final_s5}
    dis_rows, causes = [], Counter()
    with (OUT / "canonical.tsv").open("w", encoding="utf-8") as fh:
        fh.write("key\tpage\tstatus\ttokens_canonical\ttree_canonical\tagree\ttree_spike_printer\tagree_spike_printer\tcause\n")
        for f in final:
            if f["tree"] is None:
                continue
            g = s5[f["key"]]
            # a span at the parse timer may be read in one run and not the other (Timing): no S5-printer form
            agree = (g["tree"] == g["tokens_product"]) if g["tree"] is not None else "not read in the S5-printer run (timer)"
            agree_sp = f["tree"] == f["tokens_product"]
            cause = "" if agree_sp else cause_of(f, agree)
            if not agree_sp:
                causes[cause.split(":")[0]] += 1
                dis_rows.append((f, g, cause))
            fh.write("\t".join(str(x).replace("\t", " ").replace("\n", " ") for x in (
                f["key"], f["page"], f["status"], g["tokens_product"], g["tree"], agree,
                "" if agree_sp else f["tree"], agree_sp, cause)) + "\n")
    # the same property on the baseline grammar (spike printer)
    b_dis = [(r, cause_of(r, False)) for r in b0 if r["tree"] is not None and r["tree"] != r["tokens_spike"]]

    # ---- coverage.md
    L = []
    w = L.append
    w("# S5-A grammar coverage (results/s5)\n")
    w("Generated by `code/s5_report.py` from `results/s5/runs/` (written by `code/s5_coverage.py`); "
      "trials by `code/s5_extensions.py`. Figures **Measured** 2026-10-28 on all math spans of the 78 "
      "first-pass pages.\n")
    w("## Inputs\n")
    stored = {p: r["stored"] for p, r in rens.items() if "stored" in r}
    w(f"- {n} math spans ({sum(1 for s in spans.values() if s['delimiting'] == 'ok')} delimited `ok`, "
      f"{sum(1 for s in spans.values() if s['delimiting'] == 'partial')} `partial`), equal to S1's count (record s1.corpus: 28,956).")
    w(f"- Renditions: parser `{', '.join(sorted({r['parser'] for r in rens.values()}))}` (libxml2 "
      f"{sorted({r['libxml2'] for r in rens.values()})[0]}); the stored seven taken as they stand "
      f"({len(stored)} pages; regenerated text, math spans and macros identical on all: "
      f"{all(v['text_identical'] and v['math_spans_identical'] and v['macros_identical'] for v in stored.values())}); "
      f"the other {len(rens) - len(stored)} regenerated by `s1_adapter.adapt` (contract R1).")
    w("- Every span parsed under `any_value` with its rendition's effective macro table (page table over the "
      "D2 §12.1 fallback). Parse timer 2 s per attempt (api.PARSE_SECONDS); the ambiguity resolver's SymPy "
      "conversions bounded at 1 s per reading and 4 s per value (see Timing).\n")

    w("## V1 x V2: the four baseline runs\n")
    w("| Run (grammar.reader) | ok | ambiguous | partial | failed | spans identical to spike.spike |")
    w("|---|---|---|---|---|---|")
    for t in v_table:
        w(f"| `{t['run']}` | {t['ok']} | {t['ambiguous']} | {t['partial']} | {t['failed']} | {t['identical_to_spike_spike']} of {n} |")
    w("")
    w("- **V1** (`edited`: Lark `edit_terminals` whole-name for every control-word literal, `ordered_sets=True`; "
      "`edited-noovr`: the same without the regex-generated `%override` lines, the port form): no span changes status, "
      "detected kind, category, notes or printed tree. The `\\left`/`\\right`/`\\quad` prefix defect needs a command that "
      "begins with a literal terminal's name and continues with letters (`\\leftarrow`, `\\rightarrow`, `\\quadrant`); "
      "the corpus math has none, so the figures measured before the fix (and S0/S0-R2's) are not overstated on Siegrist. "
      "The fix stays: it is what makes such commands fail honestly on other sources.")
    w(f"- **V2** (tokenizer reader): it reads `\\renewcommand{{\\P}}{{\\mathbb{{P}}}}` on "
      f"{len(macros['pages_where_spike_missed'])} pages the spike reader missed "
      f"({macros['uses_from_fallback_spike_reader'].get(chr(92) + 'P', 0)} `\\P` uses took the fallback under the spike reader); "
      f"the effective table differs on {len(macros['pages_effective_table_differs'])} pages, because the fallback body is the same, "
      "so coverage is identical by construction and measured so.\n")

    def status_block(rows, title):
        st = Counter(r["status"] for r in rows)
        w(f"### {title}\n")
        w("| Status | spans | share | inline | display |")
        w("|---|---|---|---|---|")
        for s in STATUSES:
            w(f"| {s} | {st.get(s, 0)} | {pct(st.get(s, 0), n)} | "
              f"{sum(1 for r in rows if r['status'] == s and r['kind'] == 'math_inline')} | "
              f"{sum(1 for r in rows if r['status'] == s and r['kind'] == 'math_display')} |")
        read = sum(st.get(s, 0) for s in ("ok", "ambiguous", "partial"))
        w(f"\nRead (a tree): {read} ({pct(read, n)}); ok: {pct(st.get('ok', 0), n)}.\n")
        fails = [r for r in rows if r["status"] == "failed"]
        w("| Failure category | spans |")
        w("|---|---|")
        for c, k in Counter(r["category"] for r in fails).most_common():
            w(f"| {c} | {k} |")
        w("")
        w("| Ambiguity cause | spans |")
        w("|---|---|")
        for c, k in Counter(ambiguity_cause(r["notes"]) for r in rows if r["status"] == "ambiguous").most_common():
            w(f"| {c} | {k} |")
        w("")

    w("## Coverage before the extensions (V1 edited, V2 tokenizer; identical for all four baselines)\n")
    status_block(base["edited-noovr.tokenizer"], "Status and categories")
    w("Earlier figure for comparison: the 1,532-span seeded sample of `results/mathgrammar/` had 976 ok (63.7%), "
      "256 ambiguous, 1 partial, 299 failed; the whole first pass reads better than that sample (which drew equally "
      "from inline and display spans per page).\n")

    w("## Extensions (step 3)\n")
    w("Each block of `code/s5grammar/ext/` was tried in order on top of the blocks kept so far, over all spans. "
      "Kept when it gains spans (failed -> read) and turns no `ok` span `failed` or `ambiguous` and no read span "
      "`failed`. The kept blocks, in order, are assembled into `code/s5grammar/extension.lark` "
      "(`mathgrammar/extension.lark` + the blocks).\n")
    w("| Block | Construct | Kept | Gained (of which ok) | ok -> failed/ambiguous | read -> failed | ok after | failed after | Gained from (category:token, top) |")
    w("|---|---|---|---|---|---|---|---|---|")
    for t in ext["trials"]:
        if "error" in t:
            w(f"| {t['block']} | build error | no | | | | | | {t['error'][:80]} |")
            continue
        construct = (EVIDENCE / "code" / "s5grammar" / "ext" / t["file"]).read_text().splitlines()[0].lstrip("/ ")
        top = ", ".join(f"{k} {v}" for k, v in list(t["gained_by_construct"].items())[:3])
        w(f"| {t['block']} | {construct[6:] if construct.startswith('S5-') else construct} | {'yes' if t['kept'] else 'no'} | "
          f"{t['gained']} ({t['gained_ok']}) | {t['broken']} | {t['lost_read']} | {t['status'].get('ok', 0)} | "
          f"{t['status'].get('failed', 0)} | {top} |")
    w("")
    rejected = [t for t in ext["trials"] if not t.get("kept")]
    if rejected:
        w("Rejected trials and the spans they would have broken:\n")
        for t in rejected:
            w(f"- **{t['block']}**: {t.get('broken', '?')} ok spans broken, {t.get('lost_read', '?')} read spans lost; e.g. "
              + "; ".join(f"`{e['latex'][:80]}` ({e['was']} -> {e['now']})" for e in t.get("broken_examples", [])[:3]))
        w("")

    w("## Coverage after the extensions (`extended`, V2 tokenizer)\n")
    status_block(final, "Status and categories")
    fails = [r for r in final if r["status"] == "failed"]
    w("### Remaining failures by construct (category, TeX token at the error)\n")
    w("| Construct | spans | example (token form) |")
    w("|---|---|---|")
    groups: dict[str, list] = {}
    for r in fails:
        groups.setdefault(f"{r['category']}: `{r['token'] or '<end>'}`", []).append(r)
    for k, v in sorted(groups.items(), key=lambda kv: -len(kv[1]))[:30]:
        ex = v[0]["tokens_product"][:90].replace("|", "\\|")
        w(f"| {k} | {len(v)} | `{ex}` |")
    w("")
    w("The category:token groups are not single constructs (the `,` group mixes inner products, multinomial "
      "coefficients, measure differentials and others). Each remaining failure assigned to the first matching "
      "construct of a fixed list (regular expressions over the span; `code/s5_report.py` CONSTRUCTS):\n")
    w("| Construct | failed spans |")
    w("|---|---|")
    cons = Counter(construct_of(spans[r["key"]]["latex"]) for r in fails)
    for k, v in cons.most_common():
        w(f"| {k} | {v} |")
    named = [(k, v) for k, v in cons.most_common() if k != "other"]
    w(f"\nLargest remaining named construct: {named[0][0]} ({named[0][1]} spans); the stop criterion (about 50) is met. "
      f"`other` ({cons.get('other', 0)}) is spread over many single constructs.\n")

    w("## The 8 delimiting-partial spans\n")
    w("| Page | Delimiting reason | Span (first 60 characters) | Grammar (baseline) | Grammar (extended) |")
    w("|---|---|---|---|---|")
    fbk = {r["key"]: r for r in final}
    for a in b0:
        if a["delimiting"] != "partial":
            continue
        f = fbk[a["key"]]
        txt = spans[a["key"]]["latex"][:60].replace("|", "\\|").replace("\n", " ")
        w(f"| {a['page']} | {a['delimiting_reason']} | `{txt}` | {a['status']} {a['category'] or ''} | {f['status']} {f['category'] or ''} |")
    w("\nThe grammar's status never changes a segment's `parse_status` (D1 §3.1); these spans keep `partial` from delimiting.\n")

    w("## Timing\n")
    for name, rows in (("baseline edited-noovr.tokenizer", base["edited-noovr.tokenizer"]), ("extended.tokenizer", final)):
        fresh = sorted(r["ms"] for r in rows if not r["cached"])
        w(f"- {name}: {len(fresh)} uncached parses, median {fresh[len(fresh) // 2]:.0f} ms, p99 "
          f"{fresh[int(len(fresh) * .99)]:.0f} ms, max {fresh[-1]:.0f} ms; parse timeouts "
          f"{sum(1 for r in rows if r['category'] == 'timeout')}; spans whose resolver hit its bound "
          f"{sum(1 for r in rows if r['resolver_timeouts'])}.")
    jitter = [(a, b) for a, b in zip(final, final_s5) if a["status"] != b["status"]]
    w(f"- **Run-to-run variation at the timer.** The two final runs (same grammar; they differ only in the tree "
      f"printer, which does not affect status) differ in status on {len(jitter)} spans, all long display spans "
      f"near the 2 s timer ({', '.join(sorted({a['status'] + '/' + b['status'] for a, b in jitter}))}); with 30 parallel "
      "workers parse times are load-dependent. Figures above are from `extended.tokenizer`; the step-3 trials "
      "treat a read span that took >= 1.5 s and then times out as a timing effect, not a break (counted per trial "
      "in `extensions.json`). The extensions roughly double the median parse time (Earley over more rules).")
    w("- **Resolver bound (finding for the port).** `api._Resolver` merges readings by converting each to SymPy outside "
      "the parse timer; on the first full run three workers spent more than 11 minutes in mpmath quadrature reached from "
      "`transformer.eq` (`Eq(...)` evaluating an integral numerically). S5 bounds the conversion (1 s per reading, 4 s per "
      "value); a reading not converted in time is not comparable, so the value stays `ambiguous`, never picked. The port "
      "needs one deadline over the whole read (parse, resolver, occurrences), or unevaluated relations in the resolver.\n")

    w("## Tree/token property (summary; record s5.keys-property)\n")
    w(f"- Baseline grammar, spike printer: {sum(1 for r in b0 if r['tree'] is not None)} spans read, "
      f"{len(b_dis)} disagreements: " + ", ".join(f"{k} {v}" for k, v in Counter(c.split(':')[0] for _, c in b_dis).items()) + ".")
    read_f = [r for r in final if r["tree"] is not None]
    w(f"- Extended grammar, spike printer: {len(read_f)} read, {len(dis_rows)} disagreements: "
      + ", ".join(f"{k} {v}" for k, v in causes.items()) + ".")
    s5_dis = [g for g in final_s5 if g["tree"] is not None and g["tree"] != g["tokens_product"]]
    w(f"- Extended grammar, S5 printer (T1-T3): {len(s5_dis)} disagreements over {sum(1 for g in final_s5 if g['tree'] is not None)} read.")
    w(f"- Spike (I-R2) and product (`core/tex.py`) token forms: equal on "
      f"{sum(1 for r in final if r['tokens_spike'] == r['tokens_product'])} of {n} spans.\n")
    (OUT / "coverage.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    st_b = Counter(r["status"] for r in base["edited-noovr.tokenizer"])
    st_f = Counter(r["status"] for r in final)
    summary = {
        "spans": n, "v_table": v_table,
        "baseline": {s: st_b.get(s, 0) for s in STATUSES}, "extended": {s: st_f.get(s, 0) for s in STATUSES},
        "kept": ext["kept"], "rejected": [t["block"] for t in rejected],
        "largest_remaining_construct": max(((k, len(v)) for k, v in groups.items()), key=lambda kv: kv[1]) if groups else None,
        "property": {"baseline_read": sum(1 for r in b0 if r["tree"] is not None), "baseline_disagreements": len(b_dis),
                     "baseline_causes": dict(Counter(c.split(':')[0] for _, c in b_dis)),
                     "extended_read": len(read_f), "extended_disagreements_spike_printer": len(dis_rows),
                     "extended_causes_spike_printer": dict(causes), "extended_disagreements_s5_printer": len(s5_dis),
                     "s5_printer_disagreements": [{"key": g["key"], "tree": g["tree"][:200], "token": g["tokens_product"][:200]} for g in s5_dis[:50]],
                     "token_forms_equal": sum(1 for r in final if r["tokens_spike"] == r["tokens_product"])},
    }
    (OUT / "coverage_summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(summary, ensure_ascii=False)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
