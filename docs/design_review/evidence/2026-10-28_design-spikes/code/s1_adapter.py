"""S1 throwaway HTML adapter (M01 prototype): page bytes + configuration -> rendition.

A rendition is the canonical text, a segment tree with offsets, author-markup records,
excluded-content records and rendition attributes (D1 §3, D4 M01). The plan is
docs/plans/design-spikes-s0-s1/S1-ingest-segmentation.md (§3 mechanisms, §4 rules, §5 variants).

Usage (from the evidence folder):
    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/s1_adapter.py [config.json] page...
Pages are paths relative to the Siegrist corpus root (e.g. special/Normal.html).
"""

from __future__ import annotations

import copy
import hashlib
import json
import re

import regex
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import cssselect2
import lxml.html
import yaml
from lxml import etree
from lxml.cssselect import CSSSelector
from lxml.html import html5parser
from pylatexenc.latexnodes.parsers import LatexGeneralNodesParser
from pylatexenc.latexwalker import (
    LatexMacroNode,
    LatexWalker,
    LatexWalkerError,
    get_default_latex_context_db,
)
from pylatexenc.macrospec import MacroSpec

CODE = Path(__file__).resolve().parent
EVIDENCE = CODE.parent
REPO = EVIDENCE.parents[3]
CORPUS = REPO / "docs/statistics_corpus/corpus"
SIEGRIST = CORPUS / "siegrist_random/random"
PROJECT = "corpus-structure"
SID = "data-s1id"

DEFAULT_CONFIG: dict = {
    "adapter": "s1_adapter",
    "version": "0.1.0",
    "profile": "siegrist",
    "parser": "lxml",  # lxml | html5lib                        (V1)
    "unicode": "NFC",  # NFC | NFKC                             (V2)
    "math_whitespace": "keep",  # keep | collapse                (V3)
    "sections": "h3h4",  # h3h4 | h3                             (V4)
    "apps": "keep",  # keep | exclude                            (V7)
    "render": {  # rendered-only text conventions                (R1–R5)
        "aref": "browser",  # empty | placeholder | browser ("[n]" as Basic.js renders it)
        "q": "quotes",  # bare | quotes
        "list_markers": "parenthesized",  # none | parenthesized ("(a) ") | browser ("a. ")
        "summary": "heading",  # heading | drop
        "figure": "caption",  # caption | drop
    },
}

BLOCK_KIND = {
    "body": "document", "p": "paragraph", "li": "list_item", "ol": "list", "ul": "list",
    "dl": "list", "dt": "list_item", "dd": "list_item", "details": "details",
    "summary": "heading", "table": "table", "tr": "table_row", "td": "table_cell",
    "th": "table_cell", "figure": "figure", "figcaption": "caption", "blockquote": "block",
    "pre": "paragraph", "div": "division", "h1": "heading", "h2": "heading", "h3": "heading",
    "h4": "heading", "h5": "heading", "h6": "heading",
}
TRANSPARENT = {"html", "header", "thead", "tbody", "tfoot", "main", "section", "article", "nav"}
TEXT_BLOCKS = {"paragraph", "list_item", "heading", "table_cell", "caption"}
LIST_SEP_KINDS = {"list", "list_item"}


# ---------------------------------------------------------------------------- keys (D1 §10.1)

def _nfc(obj):
    if isinstance(obj, str):
        return unicodedata.normalize("NFC", obj)
    if isinstance(obj, list):
        return [_nfc(x) for x in obj]
    if isinstance(obj, dict):
        return {_nfc(k): _nfc(v) for k, v in obj.items()}
    return obj


def canonical_json(obj) -> str:
    return json.dumps(_nfc(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def make_key(prefix: str, parts) -> str:
    """D1 §10.1: prefix + ':' + hex(sha256(canonical_json(parts)))[:32]; parts as a JSON array."""
    return prefix + ":" + hashlib.sha256(canonical_json(parts).encode("utf-8")).hexdigest()[:32]


# ---------------------------------------------------------------------------- profile

def load_profile(name: str, config: dict) -> dict:
    data = yaml.safe_load((CODE / "profile" / f"{name}.yaml").read_text())
    base, add = data["d2_12_1"], data.get("s1_additions", {})
    prof = copy.deepcopy(base)
    prof["exclude"].update(add.get("exclude", {}))
    prof["block_hints"].update(add.get("block_hints", {}))
    prof["math"].update(add.get("math", {}))
    if config["apps"] == "exclude":
        prof["exclude"]["apps"] = "div.unit:has(> p.app)"
    if config["render"]["figure"] == "drop":
        prof["exclude"]["figures"] = "figure"
    if config["render"]["summary"] == "drop":
        prof["exclude"]["summaries"] = "details > summary"
    return prof


def profile_rules(prof: dict) -> list[tuple[str, tuple]]:
    """(css selector, payload) pairs; payload = (role, name, data)."""
    rules: list[tuple[str, tuple]] = []
    for name, css in prof["exclude"].items():
        rules.append((css, ("exclude", name, None)))
    rules.append((prof["unit"], ("unit", "unit", None)))
    rules.append((prof["title"], ("title", "title", None)))
    for css, hint in prof["block_hints"].items():
        rules.append((css, ("block_hint", css, hint)))
    rules.append(("details", ("details", "details", None)))
    rules.append(("details > summary", ("summary", "summary", None)))
    return rules


def match_cssselect2(root, rules) -> dict[str, list[tuple]]:
    matcher = cssselect2.Matcher()
    for css, payload in rules:
        for compiled in cssselect2.compile_selector_list(css):
            matcher.add_selector(compiled, payload)
    out: dict[str, list[tuple]] = {}
    for w in cssselect2.ElementWrapper.from_html_root(root).iter_subtree():
        hits = matcher.match(w)
        if hits:
            out[sid(w.etree_element)] = [h[3] for h in hits]
    return out


def match_xpath(root, rules) -> tuple[dict[str, list[tuple]], dict[str, str]]:
    out: dict[str, list[tuple]] = {}
    paths: dict[str, str] = {}
    for css, payload in rules:
        sel = CSSSelector(css, translator="html")
        paths[css] = sel.path
        for el in sel(root):
            out.setdefault(sid(el), []).append(payload)
    return out, paths


# ---------------------------------------------------------------------------- parsing

def parse_html(raw: bytes, parser: str):
    if parser == "lxml":
        p = lxml.html.HTMLParser(remove_comments=True, remove_pis=True)
        return lxml.html.document_fromstring(raw, parser=p)
    root = html5parser.document_fromstring(raw.decode("utf-8"))
    for el in root.iter():
        if isinstance(el.tag, str) and el.tag.startswith("{"):
            el.tag = el.tag.split("}", 1)[1]
    for c in root.xpath("//comment()"):
        parent, tail = c.getparent(), c.tail or ""
        prev = c.getprevious()
        if prev is not None:
            prev.tail = (prev.tail or "") + tail
        else:
            parent.text = (parent.text or "") + tail
        parent.remove(c)
    etree.cleanup_namespaces(root)
    return root


def stamp(root) -> None:
    """Stable element ids: lxml proxies are recreated on demand, so id(el) is not stable (lxml.md §9.5)."""
    for i, el in enumerate(root.iter()):
        if isinstance(el.tag, str):
            el.set(SID, str(i))


def sid(el) -> str:
    return el.get(SID)


def classes(el) -> list[str]:
    return (el.get("class") or "").split()


# ---------------------------------------------------------------------------- macro tables

def macro_table(root) -> dict:
    """Page \\newcommand definitions from div.latex via pylatexenc 3.0b2 (D4 M01 parse_detail.macros)."""
    table: dict = {}
    for div in root.xpath("//div[contains(concat(' ', normalize-space(@class), ' '), ' latex ')]"):
        src = "".join(div.itertext())
        nodes, _, _ = LatexWalker(src, tolerant_parsing=True).get_latex_nodes()
        stack = list(nodes)
        while stack:
            n = stack.pop(0)
            if isinstance(n, LatexMacroNode) and n.macroname == "newcommand" and n.nodeargd:
                args = n.nodeargd.argnlist  # spec "*{[[{": star, name, nargs, default, body
                name = args[1].latex_verbatim().strip("{} \t\n") if args[1] is not None else None
                nargs = int(args[2].latex_verbatim().strip("[]")) if args[2] is not None else 0
                body = args[4].latex_verbatim() if args[4] is not None else ""
                if body.startswith("{") and body.endswith("}"):
                    body = body[1:-1]
                if name:
                    table[name] = {"nargs": nargs, "body": body}
            for attr in ("nodelist",):
                stack.extend(getattr(n, attr, None) or [])
    return table


def latex_context(macros: dict):
    """Default context plus the page's macros as MacroSpecs (derived, not mutated after use)."""
    db = get_default_latex_context_db()
    specs = [MacroSpec(name.lstrip("\\"), "{" * m["nargs"]) for name, m in macros.items()]
    db.add_context_category("page-macros", prepend=True, macros=specs)
    db.freeze()
    return db


def prose_safe_state(walker: LatexWalker):
    """pylatexenc 3 ParsingState for HTML prose: math only from \\(…\\) and \\[…\\] ($ is currency),
    no comments (% is percent), no blank-line paragraph nodes."""
    return walker.make_parsing_state(
        latex_inline_math_delimiters=[("\\(", "\\)")],
        latex_display_math_delimiters=[("\\[", "\\]")],
        enable_comments=False,
        enable_double_newline_paragraphs=False,
    )


# ---------------------------------------------------------------------------- tree

@dataclass
class Run:
    """Inline text of one block between block-level children, with inline markup events."""

    pieces: list[str] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)  # raw offsets
    size: int = 0

    def add(self, text: str | None) -> None:
        if text:
            self.pieces.append(text)
            self.size += len(text)

    def raw(self) -> str:
        return "".join(self.pieces)


@dataclass
class Block:
    kind: str
    tag: str
    attrs: dict
    children: list = field(default_factory=list)
    sourceline: int | None = None


class Builder:
    def __init__(self, root, config: dict, prof: dict, payloads: dict[str, list[tuple]]):
        self.root, self.config, self.prof, self.payloads = root, config, prof, payloads
        self.exclusions: list[dict] = []
        self.units = [el for el in root.iter() if isinstance(el.tag, str) and "unit" in classes(el)]
        self.unit_index: dict[str, int] = {}
        for j, el in enumerate(self.units):  # Basic.js keeps the last match
            if el.get("id"):
                self.unit_index[el.get("id")] = j + 1
        self.aref_count = 0

    def roles(self, el) -> list[tuple]:
        return self.payloads.get(sid(el), [])

    def excluded(self, el) -> str | None:
        for role, name, _ in self.roles(el):
            if role == "exclude":
                return name
        return None

    def record_exclusion(self, el, rule: str) -> None:
        text = re.sub(r"\s+", " ", "".join(el.itertext())).strip()
        self.exclusions.append({"rule": rule, "tag": el.tag, "classes": classes(el),
                                "sourceline": el.sourceline, "chars": len(text)})

    def is_block(self, el) -> bool:
        return el.tag in BLOCK_KIND or el.tag in TRANSPARENT

    def block_kind(self, el) -> str:
        if any(r[0] == "unit" for r in self.roles(el)):
            return "unit"
        return BLOCK_KIND.get(el.tag, "division")

    def attrs(self, el) -> dict:
        a: dict = {"tag": el.tag, "sid": sid(el)}
        if el.get("id"):
            a["id"] = el.get("id")
        if classes(el):
            a["classes"] = classes(el)
        for role, name, data in self.roles(el):
            if role == "block_hint":
                a["hint"] = {"selector": name, **data}
            elif role in ("unit", "title", "details", "summary"):
                a.setdefault("roles", []).append(role)
        if el.tag == "ol" and el.get("start"):
            a["start"] = el.get("start")
        return a

    # inline content -----------------------------------------------------------
    def inline(self, el, run: Run) -> None:
        rule = self.excluded(el)
        if rule:
            self.record_exclusion(el, rule)
            return
        start = run.size
        render = self.config["render"]
        if el.tag == "q" and render["q"] == "quotes":
            run.add("“")
        if el.tag == "br":
            run.add(" ")
        if el.tag == "a" and "ref" in classes(el) and not "".join(el.itertext()).strip():
            self.aref_count += 1
            href = el.get("href") or ""
            ref = href[href.find("#") + 1:] if "#" in href else ""
            text = {"empty": "", "placeholder": "[ref]",
                    "browser": f"[{self.unit_index[ref]}]" if ref in self.unit_index else ""}[render["aref"]]
            run.add(text)
            run.events.append({"start": start, "end": run.size, "markup": "aref", "href": href,
                               "rendered": text})
            return
        run.add(el.text)
        for child in el:
            if not isinstance(child.tag, str):
                run.add(child.tail)
                continue
            self.inline(child, run)
            run.add(child.tail)
        if el.tag == "q" and render["q"] == "quotes":
            run.add("”")
        if el.tag in ("dfn", "a", "q", "em", "strong", "sub", "sup", "span"):
            ev = {"start": start, "end": run.size, "markup": el.tag}
            if el.tag == "a":
                ev["href"] = el.get("href")
                if classes(el):
                    ev["classes"] = classes(el)
            run.events.append(ev)

    # block content ------------------------------------------------------------
    def build(self, el) -> Block:
        blk = Block(self.block_kind(el), el.tag, self.attrs(el), sourceline=el.sourceline)
        run = Run()
        if el.tag == "li" and self.config["render"]["list_markers"] != "none":
            marker = self.list_marker(el)
            if marker:
                run.add(marker)
                run.events.append({"start": 0, "end": len(marker), "markup": "list_marker"})
        run.add(el.text)

        def flush():
            nonlocal run
            if run.raw().strip():
                blk.children.append(run)
            run = Run()

        for child in el:
            if not isinstance(child.tag, str):
                run.add(child.tail)
                continue
            rule = self.excluded(child)
            if rule:
                self.record_exclusion(child, rule)
                run.add(child.tail)
                continue
            if child.tag in TRANSPARENT:
                flush()
                inner = self.build(child)
                blk.children.extend(inner.children)
                run.add(child.tail)
            elif self.is_block(child):
                flush()
                blk.children.append(self.build(child))
                run.add(child.tail)
            else:
                self.inline(child, run)
                run.add(child.tail)
        flush()
        if blk.kind == "document":
            blk.children = self.sectionize(blk.children)
        return blk

    def list_marker(self, li) -> str:
        ol = li.getparent()
        if ol is None or ol.tag != "ol" or "sub" not in classes(ol):
            return ""
        start = int(ol.get("start") or 1)
        idx = [c for c in ol if isinstance(c.tag, str) and c.tag == "li"].index(li)
        letter = chr(ord("a") + start - 1 + idx)
        return {"parenthesized": f"({letter}) ", "browser": f"{letter}. "}[self.config["render"]["list_markers"]]

    def sectionize(self, children: list) -> list:
        levels = {"h3": 3, "h4": 4} if self.config["sections"] == "h3h4" else {"h3": 3}
        top: list = []
        stack: list[tuple[int, Block]] = []
        for ch in children:
            lvl = levels.get(ch.tag) if isinstance(ch, Block) and ch.kind == "heading" else None
            if lvl:
                while stack and stack[-1][0] >= lvl:
                    stack.pop()
                title = re.sub(r"\s+", " ", ch.attrs.get("_text", "")).strip()
                sec = Block("section", "section", {"level": lvl, "heading_tag": ch.tag}, [ch],
                            sourceline=ch.sourceline)
                (stack[-1][1].children if stack else top).append(sec)
                stack.append((lvl, sec))
                del title
            else:
                (stack[-1][1].children if stack else top).append(ch)
        return top


# ---------------------------------------------------------------------------- math and runs

_MATH_PATTERNS: dict = {}


def math_pattern(math_cfg) -> "regex.Pattern":
    """One `regex` pattern from the profile's math declarations (ADR-0009, revisit S1-R1):
    delimiter pairs (`inline`, `display`) and bare `display_environments`. An escaped backslash is
    skipped; a span's body stops at the next declared delimiter, so an unclosed span ends there
    (`partial`) and the scan resynchronizes; a closer outside any span is reported as stray."""
    if isinstance(math_cfg, list):  # legacy call: environments only, default delimiters
        math_cfg = {"inline": ["\\(", "\\)"], "display": ["\\[", "\\]"], "display_environments": math_cfg}
    pairs = [tuple(math_cfg[k]) for k in ("inline", "display") if math_cfg.get(k)]
    envs = list(math_cfg.get("display_environments") or [])
    key = (tuple(pairs), tuple(envs))
    if key in _MATH_PATTERNS:
        return _MATH_PATTERNS[key]
    opens = sorted({o for o, _ in pairs}, key=len, reverse=True)
    closes = sorted({c for _, c in pairs}, key=len, reverse=True)
    delims = "|".join(regex.escape(d) for d in sorted(set(opens) | set(closes), key=len, reverse=True))
    alt = [r"\\\\ (*SKIP)(*F)",
           r"(?P<open>" + "|".join(regex.escape(o) for o in opens) + r")"
           r"(?P<body>(?:\\\\ | (?!" + delims + r") .)*+)"
           r"(?P<close>" + "|".join(regex.escape(c) for c in closes) + r")?",
           r"(?P<stray>" + "|".join(regex.escape(c) for c in closes) + r")"]
    if envs:
        names = "|".join(regex.escape(e) for e in envs)
        alt.insert(1, r"(?P<env>\\begin\{(?P<name>" + names + r")\}) .*? (?P<envend>\\end\{(?P=name)\} | \Z)")
    pat = regex.compile("(?V1)" + " | ".join(alt), regex.VERBOSE | regex.DOTALL)
    _MATH_PATTERNS[key] = pat
    return pat


def scan_math(s: str, math_cfg) -> tuple[list[dict], list[dict]]:
    """Delimit math in a text run by the profile's pattern; never rewrites. Returns spans, anomalies."""
    pairs = None
    if isinstance(math_cfg, dict):
        pairs = {o: c for o, c in (math_cfg[k] for k in ("inline", "display") if math_cfg.get(k))}
    else:
        pairs = {"\\(": "\\)", "\\[": "\\]"}
    inline_open = (math_cfg.get("inline") or [None])[0] if isinstance(math_cfg, dict) else "\\("
    spans: list[dict] = []
    anomalies: list[dict] = []
    for m in math_pattern(math_cfg).finditer(s, timeout=10.0):
        if m.group("stray"):
            anomalies.append({"pos": m.start(), "kind": "stray closer", "delim": m.group("stray")})
        elif m.groupdict().get("env"):
            closed = bool(m.group("envend"))
            spans.append({"start": m.start(), "end": m.end(), "open": m.group("env"),
                          "close": m.group("envend") if closed else None, "status": "ok" if closed else "partial",
                          "reason": None if closed else f"unclosed {m.group('env')}", "display": True})
        else:
            o, c = m.group("open"), m.group("close")
            if c is None:
                reason = "unclosed at block end" if m.end() == len(s) else f"unclosed {o} before next opener"
                status = "partial"
            elif pairs.get(o) != c:
                reason, status = f"{o} closed by {c}", "partial"
            else:
                reason, status = None, "ok"
            spans.append({"start": m.start(), "end": m.end(), "open": o, "close": c, "status": status,
                          "reason": reason, "display": o != inline_open})
    return spans, anomalies


def validate_span(tex: str, ctx) -> tuple[str, str | None]:
    """pylatexenc 3.0b2, non-tolerant parse of a whole delimited span (so its inside is math mode)."""
    try:
        w = LatexWalker(tex, latex_context=ctx, tolerant_parsing=False)
        w.parse_content(LatexGeneralNodesParser(), parsing_state=prose_safe_state(w))
        return "ok", None
    except LatexWalkerError as exc:
        return "partial", f"pylatexenc: {str(exc).splitlines()[0][:160]}"


def process_run(run: Run, config: dict, prof: dict, ctx, stats: dict) -> tuple[str, list[dict], list[dict]]:
    raw = run.raw()
    spans, anomalies = scan_math(raw, prof["math"])
    stats["math_anomalies"].extend(anomalies)
    in_math = [False] * len(raw)
    for sp in spans:
        for k in range(sp["start"], sp["end"]):
            in_math[k] = True
    collapse_math = config["math_whitespace"] == "collapse"
    out: list[str] = []
    pos = [0] * (len(raw) + 1)
    for k, ch in enumerate(raw):
        pos[k] = len(out)
        if ch.isspace() and (not in_math[k] or collapse_math):
            if out and out[-1] != " ":
                out.append(" ")
        else:
            out.append(ch)
    pos[len(raw)] = len(out)
    while out and out[-1] == " ":
        out.pop()
    length = len(out)
    text = "".join(out)
    clamp = lambda p: min(p, length)  # noqa: E731
    # Unicode normalization chunk by chunk between boundaries, so boundary offsets stay exact.
    bounds = sorted({0, length} | {clamp(pos[sp["start"]]) for sp in spans} | {clamp(pos[sp["end"]]) for sp in spans}
                    | {clamp(pos[e["start"]]) for e in run.events} | {clamp(pos[e["end"]]) for e in run.events})
    newmap: dict[int, int] = {}
    pieces = []
    acc = 0
    for a, b in zip(bounds, bounds[1:], strict=False):
        newmap[a] = acc
        chunk = text[a:b]
        norm = unicodedata.normalize(config["unicode"], chunk)
        if norm != chunk:
            stats["unicode_changed"].append({"before": chunk[:80], "after": norm[:80]})
        pieces.append(norm)
        acc += len(norm)
    newmap[length] = acc
    text = "".join(pieces)
    m = lambda p: newmap[clamp(pos[p])]  # noqa: E731
    math_segs = []
    for sp in spans:
        s, e = m(sp["start"]), m(sp["end"])
        status, reason = sp["status"], sp["reason"]
        if status == "ok":
            status, reason = validate_span(text[s:e], ctx)
        math_segs.append({"kind": "math_display" if sp["display"] else "math_inline", "start": s, "end": e,
                          "attrs": {"open": sp["open"], "close": sp["close"]},
                          "parse_status": status, "reason": reason})
    markup = []
    for ev in run.events:
        rec = dict(ev)
        rec["start"], rec["end"] = m(ev["start"]), m(ev["end"])
        markup.append(rec)
    return text, math_segs, markup


# ---------------------------------------------------------------------------- serialization

def separator(kind: str) -> str:
    if kind in LIST_SEP_KINDS or kind == "table":
        return "\n"
    if kind == "table_row":
        return "\t"
    return "\n\n"


def serialize(blk: Block, config, prof, ctx, stats) -> tuple[str, dict]:
    """Returns (text, segment tree with offsets relative to text)."""
    parts: list[str] = []
    children: list[dict] = []
    markup: list[dict] = []
    offset = 0
    sep = separator(blk.kind)
    has_blocks = any(isinstance(c, Block) for c in blk.children)
    for ch in blk.children:
        if isinstance(ch, Run):
            text, math_segs, mk = process_run(ch, config, prof, ctx, stats)
            if not text:
                continue
            if blk.kind in TEXT_BLOCKS and not has_blocks:
                seg_children = math_segs
                own = None
            elif blk.kind in TEXT_BLOCKS:  # text of a list item (etc.) that also holds a nested list or table
                own = {"kind": "paragraph", "start": 0, "end": len(text),
                       "attrs": {"inline_text_of": blk.kind}, "parse_status": "ok", "children": math_segs}
            else:  # text directly in a container: an orphan paragraph (e.g. after parser repair)
                own = {"kind": "paragraph", "start": 0, "end": len(text),
                       "attrs": {"orphan": True, "container": blk.kind}, "parse_status": "ok",
                       "children": math_segs}
                stats["orphans"].append({"container": blk.kind, "sourceline": blk.sourceline,
                                         "text": text[:80]})
        else:
            text, own = serialize(ch, config, prof, ctx, stats)
            if not text:
                continue
            seg_children, mk = [], []
        if own is not None and isinstance(ch, Run):
            own["markup"] = mk
            mk = []
        if parts:
            parts.append(sep)
            offset += len(sep)
        for s in ([own] if own else seg_children):
            shift(s, offset)
            children.append(s)
        for r in mk:
            r = dict(r)
            r["start"] += offset
            r["end"] += offset
            markup.append(r)
        if own and own.get("markup"):
            pass
        parts.append(text)
        offset += len(text)
    text = "".join(parts)
    seg = {"kind": blk.kind, "start": 0, "end": len(text), "attrs": dict(blk.attrs),
           "parse_status": "ok", "children": children, "sourceline": blk.sourceline}
    seg["attrs"].pop("_text", None)
    if markup:
        seg["markup"] = markup
    return text, seg


def shift(seg: dict, d: int) -> None:
    seg["start"] += d
    seg["end"] += d
    for r in seg.get("markup", []):
        r["start"] += d
        r["end"] += d
    for c in seg.get("children", []):
        shift(c, d)


def flatten(seg: dict, rendition: str, text: str, out: list, markup_out: list, parent: str | None = None) -> None:
    key = make_key("seg", [rendition, seg["kind"], seg["start"], seg["end"]])
    rec = {"key": key, "kind": seg["kind"], "start": seg["start"], "end": seg["end"], "parent": parent,
           "attrs": seg["attrs"], "parse_status": seg["parse_status"]}
    if seg.get("reason"):
        rec["reason"] = seg["reason"]
    if seg.get("sourceline"):
        rec["attrs"] = dict(rec["attrs"], sourceline=seg["sourceline"])
    out.append(rec)
    for r in seg.get("markup", []):
        markup_out.append({**r, "segment": key, "text": text[r["start"]:r["end"]]})
    for c in seg.get("children", []):
        flatten(c, rendition, text, out, markup_out, key)


def hint_attrs(segments: list[dict], prof: dict) -> None:
    """Statement-kind hints: unit hint from its first hinted paragraph; section hints by h3 title."""
    by_key = {s["key"]: s for s in segments}
    children: dict[str, list[dict]] = {}
    for s in segments:
        if s["parent"]:
            children.setdefault(s["parent"], []).append(s)
    for s in segments:
        if s["kind"] == "unit":
            for c in children.get(s["key"], []):
                if "hint" in c["attrs"]:
                    s["attrs"]["hint"] = c["attrs"]["hint"]
                    break
    del by_key


def section_hint_attrs(segments: list[dict], prof: dict) -> None:
    """D2 §12.1 section_hints: units under a section titled e.g. "Computational Exercises" are
    exercises (innermost matching section of any level; D2 says h3, but the title is an h4 on
    some pages); the section hint takes precedence over the block-class hint, and both are kept."""
    hints = prof.get("section_hints", {})
    by_key = {s["key"]: s for s in segments}
    for s in segments:
        if s["kind"] != "unit":
            continue
        p = s
        while p.get("parent"):
            p = by_key[p["parent"]]
            if p["kind"] == "section":  # any level: "Computational Exercises" is an h4 on some pages
                title = (p["attrs"].get("title") or "").strip()
                if title in hints:
                    block = s["attrs"].get("hint")
                    s["attrs"]["hint"] = {"selector": f"section:{title}", "statement_kind": hints[title],
                                          **({"block_hint": block} if block else {})}
                break


# ---------------------------------------------------------------------------- driver

def adapt(page: str, config: dict | None = None) -> dict:
    config = merge(DEFAULT_CONFIG, config or {})
    raw = (SIEGRIST / page).read_bytes()
    root = parse_html(raw, config["parser"])
    stamp(root)
    prof = load_profile(config["profile"], config)
    rules = profile_rules(prof)
    payloads = match_cssselect2(root, rules)
    xpath_payloads, xpaths = match_xpath(root, rules)
    agreement = compare_payloads(payloads, xpath_payloads)
    macros = macro_table(root)
    ctx = latex_context(macros)
    body = root.find("body")
    b = Builder(root, config, prof, payloads)
    tree = b.build(body)
    stats = {"math_anomalies": [], "unicode_changed": [], "orphans": []}
    text, seg = serialize(tree, config, prof, ctx, stats)
    source_uri = "siegrist_random/random/" + page
    doc_key = make_key("doc", [PROJECT, source_uri, hashlib.sha256(raw).hexdigest()])
    cfg_hash = hashlib.sha256(canonical_json(config).encode()).hexdigest()[:32]
    ren_key = make_key("ren", [doc_key, cfg_hash])
    segments: list[dict] = []
    markup: list[dict] = []
    flatten(seg, ren_key, text, segments, markup)
    add_titles(segments, text)
    hint_attrs(segments, prof)
    section_hint_attrs(segments, prof)
    title_el = CSSSelector(prof["title"], translator="html")(root)
    return {
        "page": page,
        "text": text,
        "segments": segments,
        "markup": markup,
        "exclusions": b.exclusions,
        "rendition": {
            "page": page, "source_uri": source_uri, "document_key": doc_key, "rendition_key": ren_key,
            "config": config, "config_hash": cfg_hash,
            "title": re.sub(r"\s+", " ", "".join(title_el[0].itertext())).strip() if title_el else None,
            "meta": {m.get("name"): m.get("content") for m in root.xpath("//meta[@name]")},
            "parse_detail": {"macros": macros, "math_anomalies": stats["math_anomalies"],
                             "orphans": stats["orphans"], "unicode_changed": stats["unicode_changed"],
                             "aref_rendered": b.aref_count},
            "parser": config["parser"], "libxml2": ".".join(map(str, etree.LIBXML_VERSION)),
            "profile_engines": agreement, "profile_xpaths": xpaths,
        },
    }


def add_titles(segments: list[dict], text: str) -> None:
    for s in segments:
        if s["kind"] == "heading":
            s["attrs"]["_title"] = text[s["start"]:s["end"]]
    by_parent: dict[str, list[dict]] = {}
    for s in segments:
        by_parent.setdefault(s["parent"], []).append(s)
    for s in segments:
        if s["kind"] == "section":
            head = next((c for c in by_parent.get(s["key"], []) if c["kind"] == "heading"), None)
            s["attrs"]["title"] = text[head["start"]:head["end"]] if head else None
    for s in segments:
        s["attrs"].pop("_title", None)


def compare_payloads(a: dict[str, list[tuple]], b: dict[str, list[tuple]]) -> dict:
    """V5: cssselect2 Matcher versus cssselect→XPath node sets, per rule, plus conflicts."""
    def by_rule(d):
        out: dict[str, set[str]] = {}
        for el, ps in d.items():
            for p in ps:
                out.setdefault(f"{p[0]}:{p[1]}", set()).add(el)
        return out
    ra, rb = by_rule(a), by_rule(b)
    rules = sorted(set(ra) | set(rb))
    per_rule = {r: {"cssselect2": len(ra.get(r, ())), "xpath": len(rb.get(r, ())),
                    "identical": ra.get(r, set()) == rb.get(r, set())} for r in rules}
    conflicts = [sorted({f"{p[0]}:{p[1]}" for p in ps}) for ps in a.values()
                 if len({p[0] for p in ps if p[0] in ("exclude", "unit", "title")}) > 1]
    return {"per_rule": per_rule, "all_identical": all(v["identical"] for v in per_rule.values()),
            "role_conflicts": conflicts}


def merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = merge(out[k], v)
        else:
            out[k] = v
    return out


def write(result: dict, outdir: Path) -> None:
    name = result["page"].replace("/", "__").removesuffix(".html")
    for sub in ("canonical", "segments", "markup"):
        (outdir / sub).mkdir(parents=True, exist_ok=True)
    (outdir / "canonical" / f"{name}.txt").write_text(result["text"], encoding="utf-8")
    with (outdir / "segments" / f"{name}.jsonl").open("w", encoding="utf-8") as f:
        for s in result["segments"]:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    with (outdir / "markup" / f"{name}.jsonl").open("w", encoding="utf-8") as f:
        for s in result["markup"]:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")


def main(argv: list[str]) -> int:
    config = {}
    if argv and argv[0].endswith(".json"):
        config = json.loads(Path(argv.pop(0)).read_text())
    outdir = EVIDENCE / "results" / "s1"
    renditions = {}
    for page in argv:
        r = adapt(page, config)
        write(r, outdir)
        renditions[page] = r["rendition"]
        print(page, len(r["text"]), "chars,", len(r["segments"]), "segments")
    (outdir / "renditions.json").write_text(json.dumps(renditions, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
