"""P1 (2026-10-28): html5lib through lxml.html.html5parser on the 78 first-pass Siegrist pages.

    cd docs/design_review/evidence/2026-10-28_design-spikes
    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python ../2026-10-28_library-text-math/p1_html5lib.py

Questions: tag namespaces under the default parser and under namespaceHTMLElements=False; whether
CSSSelector (cssselect->XPath) and cssselect2 match on each tree; sourceline; comments; html5lib
parse errors and DataLossWarnings; bytes versus str input; parse time against libxml2.
Read-only; prints a JSON summary.
"""
import csv, json, statistics, sys, time, warnings
from pathlib import Path

import cssselect2
import lxml.html
from html5lib.constants import DataLossWarning
from lxml.cssselect import CSSSelector
from lxml.html import html5parser

REPO = Path(__file__).resolve().parents[4]
SIEG = REPO / "docs/statistics_corpus/corpus/siegrist_random/random"
pages = [r["path"] for r in csv.DictReader((REPO / "docs/statistics_corpus/index/siegrist_sections.tsv").open(), delimiter="\t")
         if r["first_pass"] == "yes"]

def count_ns(root):
    n = sum(1 for el in root.iter() if isinstance(el.tag, str) and el.tag.startswith("{"))
    return n

out = {"pages": len(pages), "t_lxml": [], "t_h5_str": [], "t_h5_bytes": [], "ns_default": 0, "ns_off": 0,
       "foreign_ns_tags": set(), "css_xpath_default": 0, "css_xpath_off": 0, "css2_default": 0, "css2_off": 0,
       "sourceline_not_none_h5": 0, "comments_h5": 0, "h5_errors": 0, "h5_error_codes": {}, "dataloss": 0,
       "bytes_vs_str_text_equal": 0, "encoding": {}}
sel = CSSSelector("div.unit", translator="html")
c2 = cssselect2.compile_selector_list("div.unit")
for p in pages:
    raw = (SIEG / p).read_bytes()
    t = time.perf_counter(); lroot = lxml.html.document_fromstring(raw); out["t_lxml"].append(time.perf_counter() - t)
    t = time.perf_counter(); d_root = html5parser.document_fromstring(raw.decode("utf-8")); out["t_h5_str"].append(time.perf_counter() - t)
    parser = html5parser.HTMLParser(namespaceHTMLElements=False)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always", DataLossWarning)
        t = time.perf_counter(); o_root = html5parser.document_fromstring(raw, parser=parser); out["t_h5_bytes"].append(time.perf_counter() - t)
        out["dataloss"] += sum(1 for x in w if issubclass(x.category, DataLossWarning))
    out["encoding"][parser.documentEncoding] = out["encoding"].get(parser.documentEncoding, 0) + 1
    out["h5_errors"] += len(parser.errors)
    for _pos, code, _v in parser.errors:
        out["h5_error_codes"][code] = out["h5_error_codes"].get(code, 0) + 1
    out["ns_default"] += count_ns(d_root)
    out["ns_off"] += count_ns(o_root)
    out["foreign_ns_tags"] |= {el.tag.split("}")[0] + "}" for el in o_root.iter() if isinstance(el.tag, str) and el.tag.startswith("{")}
    out["css_xpath_default"] += len(sel(d_root)); out["css_xpath_off"] += len(sel(o_root))
    out["css2_default"] += sum(1 for _ in cssselect2.ElementWrapper.from_html_root(d_root).query_all(*c2))
    out["css2_off"] += sum(1 for _ in cssselect2.ElementWrapper.from_html_root(o_root).query_all(*c2))
    out["sourceline_not_none_h5"] += sum(1 for el in o_root.iter() if el.sourceline is not None)
    out["comments_h5"] += len(o_root.xpath("//comment()"))
    out["bytes_vs_str_text_equal"] += "".join(o_root.itertext()) == "".join(
        html5parser.document_fromstring(raw.decode("utf-8"), parser=html5parser.HTMLParser(namespaceHTMLElements=False)).itertext())
out["lxml_units"] = None
summ = {k: (v if not isinstance(v, list) else {"total_s": round(sum(v), 2), "median_ms": round(statistics.median(v) * 1000, 1),
                                                 "max_ms": round(max(v) * 1000, 1)}) for k, v in out.items()}
summ["foreign_ns_tags"] = sorted(out["foreign_ns_tags"])
summ["root_type"] = type(o_root).__name__
print(json.dumps(summ, indent=1, default=str))
