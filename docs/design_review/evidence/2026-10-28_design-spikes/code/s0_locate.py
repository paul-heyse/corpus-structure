"""Quote locator and stored-form conversion for S0 (instruments §3; D4 §4.3 step 2; D5 §5.6).

Library use::

    ctx = UnitContext(text=canonical, unit_ranges=[(s, e)], sentences={"s1": (a, b), ...},
                      unit_keys=["seg:..."], sentence_keys={"s1": "seg:..."},
                      section_of=lambda off: "seg:...", statement_scope=lambda keys: "seg:...",
                      document_key="doc:...")
    stored, report = to_stored(model_batch_dict, ctx)

CLI (one batch)::

    python code/s0_locate.py BATCH.json --context CONTEXT.json [--out STORED.json]

where CONTEXT.json holds ``text_path`` (or ``text``), ``unit_ranges``, ``sentences``
(``{sid: [start, end]}``), optional ``unit_keys``, ``sentence_keys``, ``document_key``,
``sections`` (``[[start, end, key], ...]``), ``segments`` (``[[start, end, key], ...]``,
any non-sentence segments, used for the default ``statement_scope``) and ``macros`` (the page's
``parse_detail.macros``, for the macro step).

Cascade (D4 §4.3 step 2, instruments revisit I-R1; measured in code/regex_probe.py). Every
result records its step, tier number, the number of matches and, for the fuzzy step, the
RapidFuzz score and the regex fuzzy counts (substitutions, insertions, deletions):

  1 ``exact_sentence``  exact in the cited sentence
  2 ``exact_unit``      exact in the unit (the occurrence nearest the cited sentence)
  3 ``spacing``         exact up to spacing: a ``regex`` pattern over the original text, the quote's
                        non-space characters joined by ``(?:\\s|\\[,;!]|\\[()\\[\\]])*``; a math
                        delimiter in the quote (``$``, ``$$``, ``\\(``, ``\\)``, ``\\[``, ``\\]``) is an optional
                        delimiter (D4: "$...$ and \\(...\\) are equivalent"); cited sentence, then unit
  4 ``macros``          as 3, with each nargs-0 macro of the page (D2 §12.1 fallback beneath) or
                        its body in the quote matching either spelling in the text (\\R = \\mathbb{R})
  5 ``fuzzy``           RapidFuzz ``partial_ratio_alignment`` (cutoff 85) of the quote stripped of
                        trailing ``.,;:`` within the cited sentence; refined inside that window
                        widened by 30% of the quote length with ``regex`` BESTMATCH
                        ``(?b)(?:quote){e<=ceil(0.15 len)}`` (timeout 0.2 s); the RapidFuzz window
                        when the refine finds nothing (``fuzzy_window``)

Every located span is snapped outward to word boundaries (within the sentence or unit). Offsets
are always the original text's: no offset map. Unlocated: the cited sentence's span with
``coarse: true``; without a valid cited sentence the item is dropped as malformed.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

import math
import time

import regex
from rapidfuzz import fuzz

sys.path.insert(0, str(Path(__file__).resolve().parent))

from instruments.batch import load_batch  # noqa: E402
from instruments.conditions import as_dict, entity_positions, formula_positions  # noqa: E402

FUZZY_CUTOFF = 85
FUZZY_OPTIMAL_MAX = 64  # RapidFuzz: partial_ratio is optimal only up to 64 chars of the shorter string
REFINE_PAD = 0.30  # window widening, share of the quote length
REFINE_ERRORS = 0.15  # BESTMATCH error budget, share of the quote length
REFINE_TIMEOUT = 0.2  # seconds
JOIN = r"(?:\s|\\[,;!]|\\[()\[\]])*?"  # spacing, spacing commands, math delimiters (lazy)
OPT_DELIM = r"(?:(?:\s|\\[,;!])*?(?:\\[()\[\]]|\$\$?))?"  # a quote's delimiter: optional, preferred
STEPS = {"exact_sentence": 1, "exact_unit": 2, "spacing": 3, "macros": 4, "fuzzy": 5, "fuzzy_window": 5}


@dataclass
class UnitContext:
    text: str
    unit_ranges: list[tuple[int, int]]
    sentences: dict[str, tuple[int, int]]
    unit_keys: list[str] = field(default_factory=list)
    sentence_keys: dict[str, str] = field(default_factory=dict)
    section_of: Callable[[int], str | None] | None = None
    statement_scope: Callable[[list[str]], str | None] | None = None
    document_key: str | None = None
    macros: dict | None = None  # the page's parse_detail.macros (D2 §12.1 fallback beneath)

    def sentence_span(self, sid):
        return self.sentences.get(sid) if sid is not None else None


@dataclass
class Located:
    start: int | None
    end: int | None
    tier: int | None  # 1-5 (STEPS), None when unlocated
    scope: str | None = None  # sentence | unit
    matches: int = 0  # matches at the deciding step; >1 = ambiguous
    score: float | None = None  # RapidFuzz score (fuzzy step)
    long_quote: bool = False
    coarse: bool = False
    dropped: bool = False
    note: str = ""
    step: str | None = None  # exact_sentence | exact_unit | spacing | macros | fuzzy | fuzzy_window
    fuzzy_counts: tuple | None = None  # (substitutions, insertions, deletions) of the regex refine
    ms: float = 0.0


def _occurrences(hay: str, needle: str, base: int) -> list[int]:
    out, i = [], hay.find(needle)
    while i >= 0:
        out.append(base + i)
        i = hay.find(needle, i + 1)
    return out


def snap(text: str, a: int, b: int, lo: int, hi: int) -> tuple[int, int]:
    """Widen [a, b) outward so it neither starts nor ends inside a word (within [lo, hi))."""
    while lo < a < len(text) and text[a - 1].isalnum() and text[a].isalnum():
        a -= 1
    while 0 < b < hi and text[b - 1].isalnum() and text[b].isalnum():
        b += 1
    return a, b


_QUOTE_DELIM = regex.compile(r"\$\$|\$|\\[()\[\]]")


def spacing_pattern(quote: str, macros: dict[str, str] | None = None) -> str:
    """Regex for the quote up to spacing (and, with ``macros``, macro spelling)."""
    parts: list[str] = []
    i, q = 0, quote
    alts = []
    for name, body in sorted((macros or {}).items(), key=lambda kv: -len(kv[0])):
        name_pat = regex.escape(name) + r"(?![A-Za-z])"
        body_pat = JOIN.join(regex.escape(c) for c in body if not c.isspace())
        alts.append((regex.compile(name_pat), regex.compile(body_pat), f"(?:{name_pat}|{body_pat})"))
    while i < len(q):
        c = q[i]
        if c.isspace():
            i += 1
            continue
        m = _QUOTE_DELIM.match(q, i)
        if m:
            parts.append(OPT_DELIM)
            i = m.end()
            continue
        hit = None
        for name_re, body_re, either in alts:
            mm = name_re.match(q, i) or body_re.match(q, i)
            if mm and mm.end() > i:
                hit = (mm.end(), either)
                break
        if hit:
            parts.append(hit[1])
            i = hit[0]
            continue
        parts.append(regex.escape(c))
        i += 1
    return JOIN.join(parts)


def _page_macros(ctx: UnitContext) -> dict[str, str]:
    from instruments.values import merged_macros

    return {n: m["body"] for n, m in merged_macros(ctx.macros).items() if int(m.get("nargs") or 0) == 0}


def _search_all(pat: str, text: str, ranges: list[tuple[int, int]]) -> list[tuple[int, int, int, int]]:
    out = []
    for lo, hi in ranges:
        try:
            for m in regex.finditer(pat, text, pos=lo, endpos=hi, timeout=1.0):
                if m.end() > m.start():
                    out.append((m.start(), m.end(), lo, hi))
        except TimeoutError:
            pass
    return out


def locate_quote(quote: str, sentence: str | None, ctx: UnitContext) -> Located:
    """D4 §4.3 step 2 for one quote cited in ``sentence`` (an id, or None)."""
    t0 = time.perf_counter()
    res = _locate(quote, sentence, ctx)
    res.ms = round((time.perf_counter() - t0) * 1000, 3)
    return res


def _found(text, a, b, lo, hi, step, scope, matches, long_q, **kw) -> Located:
    while a < b and text[a].isspace():  # an optional leading delimiter may let a match start on a space
        a += 1
    while b > a and text[b - 1].isspace():
        b -= 1
    a, b = snap(text, a, b, lo, hi)
    return Located(a, b, STEPS[step], scope, matches, long_quote=long_q, step=step, **kw)


def _locate(quote: str, sentence: str | None, ctx: UnitContext) -> Located:
    text = ctx.text
    sent = ctx.sentence_span(sentence)
    long_q = len(quote) > FUZZY_OPTIMAL_MAX
    if not quote.strip():
        return Located(*(sent or (None, None)), None, coarse=sent is not None, dropped=sent is None, note="empty quote")
    anchor = sent[0] if sent else ctx.unit_ranges[0][0]
    # 1 exact in the cited sentence
    if sent:
        occ = _occurrences(text[sent[0]: sent[1]], quote, sent[0])
        if occ:
            return _found(text, occ[0], occ[0] + len(quote), sent[0], sent[1], "exact_sentence", "sentence", len(occ), long_q)
    # 2 exact in the unit (nearest occurrence to the cited sentence when several)
    occ = [(o, lo, hi) for lo, hi in ctx.unit_ranges for o in _occurrences(text[lo:hi], quote, lo) if o + len(quote) <= hi]
    if occ:
        o, lo, hi = min(occ, key=lambda x: (abs(x[0] - anchor), x[0]))
        return _found(text, o, o + len(quote), lo, hi, "exact_unit", "unit", len(occ), long_q)
    # 3 exact up to spacing, 4 the same with macro spellings: cited sentence, then unit
    for step, macros in (("spacing", None), ("macros", _page_macros(ctx))):
        pat = spacing_pattern(quote, macros)
        for scope, ranges in (("sentence", [sent] if sent else []), ("unit", ctx.unit_ranges)):
            hits = _search_all(pat, text, ranges)
            if hits:
                a, b, lo, hi = min(hits, key=lambda h: (abs(h[0] - anchor), h[0]))
                return _found(text, a, b, lo, hi, step, scope, len(hits), long_q)
    # 5 fuzzy within the cited sentence: RapidFuzz window, regex BESTMATCH refine
    if sent:
        lo, hi = sent
        qq = quote.rstrip(".,;:") or quote
        r = fuzz.partial_ratio_alignment(qq, text[lo:hi], score_cutoff=FUZZY_CUTOFF)
        if r is not None:
            pad = math.ceil(REFINE_PAD * len(qq))
            wlo, whi = max(lo, lo + r.dest_start - pad), min(hi, lo + r.dest_end + pad)
            k = max(1, math.ceil(REFINE_ERRORS * len(qq)))
            m = None
            try:
                m = regex.search(r"(?b)(?:" + regex.escape(qq) + "){e<=" + str(k) + "}", text, pos=wlo, endpos=whi,
                                 timeout=REFINE_TIMEOUT)
            except TimeoutError:
                m = None
            if m is not None and m.end() > m.start():
                return _found(text, m.start(), m.end(), lo, hi, "fuzzy", "sentence", 1, long_q,
                              score=round(r.score, 1), fuzzy_counts=tuple(m.fuzzy_counts))
            return _found(text, lo + r.dest_start, lo + r.dest_end, lo, hi, "fuzzy_window", "sentence", 1, long_q,
                          score=round(r.score, 1), note="regex refine found nothing; RapidFuzz window")
        return Located(lo, hi, None, coarse=True, long_quote=long_q, note="unlocated; cited sentence span")
    return Located(None, None, None, dropped=True, long_quote=long_q, note="unlocated and no valid cited sentence")


# ============================================================================ conversion


@dataclass
class LocateRecord:
    loc: str
    quote: str
    sentence: str | None
    result: Located


@dataclass
class LocateReport:
    records: list[LocateRecord] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)  # unresolved anchors, extents, dropped items

    def by_tier(self) -> dict:
        out: dict = {}
        for r in self.records:
            k = "dropped" if r.result.dropped else ("coarse" if r.result.coarse else r.result.step)
            out[k] = out.get(k, 0) + 1
        return out

    def ambiguous(self) -> list[LocateRecord]:
        return [r for r in self.records if r.result.matches > 1]

    def unlocated(self) -> list[LocateRecord]:
        return [r for r in self.records if r.result.tier is None]

    def as_json(self) -> dict:
        return {"by_tier": self.by_tier(), "problems": self.problems,
                "records": [{"loc": r.loc, "quote": r.quote, "sentence": r.sentence, **asdict(r.result)} for r in self.records]}


def _span_for(rep: LocateReport, loc: str, quote: str, sid: str | None, ctx: UnitContext) -> Located:
    res = locate_quote(quote, sid, ctx)
    rep.records.append(LocateRecord(loc, quote, sid, res))
    return res


def _anchor_keys(anchor, ctx: UnitContext, rep: LocateReport, loc: str) -> list[str]:
    if anchor == "unit":
        if not ctx.unit_keys:
            rep.problems.append(f"{loc}: anchor 'unit' but no unit key in the context")
        return list(ctx.unit_keys)
    keys = []
    for sid in anchor:
        k = ctx.sentence_keys.get(sid)
        if k is None:
            rep.problems.append(f"{loc}: anchor sentence {sid!r} has no segment key")
        else:
            keys.append(k)
    return keys


def _anchor_offsets(anchor, ctx: UnitContext) -> tuple[int, int] | None:
    if anchor == "unit":
        return ctx.unit_ranges[0] if ctx.unit_ranges else None
    spans = [ctx.sentences[s] for s in anchor if s in ctx.sentences]
    return (min(s for s, _ in spans), max(e for _, e in spans)) if spans else None


def _locate_phrase(node: dict, rep: LocateReport, loc: str, ctx: UnitContext) -> dict:
    """Model-facing phrase value / phrase or unsupported node -> stored (start, end)."""
    res = _span_for(rep, loc, node.get("text", ""), node.get("sentence"), ctx)
    out = {k: v for k, v in node.items() if k not in ("sentence", "quote")}
    if res.dropped:
        rep.problems.append(f"{loc}: phrase unlocated and without a valid sentence; kept without span")
        return out
    out["start"], out["end"] = res.start, res.end
    if res.coarse:
        out["coarse"] = True
    else:
        out["text"] = ctx.text[res.start : res.end]
    return out


def _convert_tree(tree, rep, loc, ctx):
    tree = as_dict(tree)
    if not isinstance(tree, dict):
        return tree
    op = tree.get("op")
    if op in ("phrase", "unsupported"):
        return _locate_phrase(tree, rep, loc, ctx)
    out = dict(tree)
    if op in ("and", "or"):
        out["args"] = [_convert_tree(a, rep, f"{loc}.args[{i}]", ctx) for i, a in enumerate(tree.get("args", []))]
    elif op == "not":
        out["arg"] = _convert_tree(tree.get("arg"), rep, f"{loc}.arg", ctx)
    elif op == "forall":
        out["body"] = _convert_tree(tree.get("body"), rep, f"{loc}.body", ctx)
    return out


def _entity_mentions(batch: dict) -> dict[str, list[dict]]:
    """Claims that mention each entity: subject, object ref, entity qualifiers, ``variable`` /
    ``family_param`` bindings of any formula, ``pred`` arguments of condition trees."""
    ents = {e.get("local_ref") for e in batch.get("entities", [])}
    out: dict[str, list[dict]] = {}

    def add(r, c):
        if r in ents and c not in out.setdefault(r, []):
            out[r].append(c)

    def value(v, c):
        if isinstance(v, str):
            add(v, c)  # bare local ref in an entity position
        elif isinstance(v, dict) and "op" in v:
            for _, fv in formula_positions(v):
                for b in (fv.get("symbols") or {}).values():
                    add(as_dict(b).get("entity"), c)
            for r in entity_positions(v):
                add(r, c)
        elif isinstance(v, dict) and ("ref" in v and v.get("t") in (None, "entity")):
            add(v["ref"], c)
        elif isinstance(v, dict) and v.get("t") in ("formula", "set"):
            for b in (v.get("symbols") or {}).values():
                add(as_dict(b).get("entity"), c)
        elif isinstance(v, dict) and "t" not in v:  # a map qualifier
            for x in v.values():
                value(x, c)

    for c in batch.get("claims", []):
        add(c.get("subject"), c)
        value(c.get("object"), c)
        for q in (c.get("qualifiers") or {}).values():
            value(q, c)
    return out


def to_stored(batch: dict, ctx: UnitContext) -> tuple[dict, LocateReport]:
    """Convert a model-facing batch dict into the stored form (D2 §7.3) on ``ctx``."""
    _, batch = load_batch(batch) if isinstance(batch, dict) and "batch" in batch else (None, batch)
    rep = LocateReport()
    out = copy.deepcopy(batch)
    stmt_anchor: dict[str, list[str]] = {}
    stmt_offsets: dict[str, tuple[int, int] | None] = {}
    for i, s in enumerate(out.get("statements", [])):
        anchor = s.get("anchor", [])
        stmt_offsets[s.get("local_ref")] = _anchor_offsets(anchor, ctx)
        s["anchor"] = _anchor_keys(anchor, ctx, rep, f"statements[{i}]")
        stmt_anchor[s.get("local_ref")] = s["anchor"]
    ev_start: dict[str, int] = {}
    for i, c in enumerate(out.get("claims", [])):
        new_ev = []
        for k, ev in enumerate(c.get("evidence", [])):
            res = _span_for(rep, f"claims[{i}].evidence[{k}]", ev.get("quote", ""), ev.get("sentence"), ctx)
            if res.dropped:
                rep.problems.append(f"claims[{i}].evidence[{k}]: dropped as malformed ({res.note})")
                continue
            item = {"start": res.start, "end": res.end, "role": ev.get("role")}
            if res.coarse:
                item["coarse"] = True
            new_ev.append(item)
        c["evidence"] = new_ev
        if new_ev:
            ev_start[c.get("local_ref")] = min(e["start"] for e in new_ev)
        obj = c.get("object")
        if isinstance(obj, dict) and obj.get("t") == "phrase":
            c["object"] = _locate_phrase(obj, rep, f"claims[{i}].object", ctx)
        quals = c.get("qualifiers") or {}
        for name, val in list(quals.items()):
            loc = f"claims[{i}].qualifiers.{name}"
            if isinstance(val, dict) and "op" in val:
                quals[name] = _convert_tree(val, rep, loc, ctx)
            elif isinstance(val, dict) and val.get("t") == "phrase":
                quals[name] = _locate_phrase(val, rep, loc, ctx)
            elif name == "scope" and isinstance(val, str):
                seg = None
                if val == "section":
                    off = ev_start.get(c.get("local_ref"))
                    seg = ctx.section_of(off) if (ctx.section_of and off is not None) else None
                elif val == "statement":
                    keys = stmt_anchor.get(c.get("statement"), [])
                    seg = _statement_scope(keys, ctx)
                elif val == "document":
                    seg = ctx.document_key
                if seg is None:
                    rep.problems.append(f"{loc}: scope {val!r} could not be resolved to a segment")
                quals[name] = {"extent": val, "segment": seg}
    for i, u in enumerate(out.get("unsupported", [])):
        res = _span_for(rep, f"unsupported[{i}]", u.pop("quote", ""), u.get("sentence"), ctx)
        u.pop("sentence", None)
        if res.dropped:
            rep.problems.append(f"unsupported[{i}]: dropped as malformed ({res.note})")
            u["_drop"] = True
            continue
        u["start"], u["end"] = res.start, res.end
        if res.coarse:
            u["coarse"] = True
    out["unsupported"] = [u for u in out.get("unsupported", []) if not u.pop("_drop", False)]
    # extent -> scope_segment
    mentions = _entity_mentions(out)
    stmts = [s.get("local_ref") for s in out.get("statements", [])]
    for i, e in enumerate(out.get("entities", [])):
        if e.get("scope") != "local":
            continue
        r = e.get("local_ref")
        claims = mentions.get(r, [])
        binding_stmt = None
        cands = [c for c in claims if c.get("statement")]
        if cands:
            cands.sort(key=lambda c: (ev_start.get(c.get("local_ref"), 10**12), stmts.index(c["statement"]) if c["statement"] in stmts else 10**6))
            binding_stmt = cands[0]["statement"]
        elif len(stmts) == 1:
            binding_stmt = stmts[0]
        starts = [ev_start[c["local_ref"]] for c in claims if c.get("local_ref") in ev_start]
        seg = None
        if e.get("extent") == "statement":
            if binding_stmt is None:
                rep.problems.append(f"entities[{i}] {r!r}: no binding statement for extent 'statement'")
            else:
                seg = _statement_scope(stmt_anchor.get(binding_stmt, []), ctx)
                if seg is None:
                    rep.problems.append(f"entities[{i}] {r!r}: statement {binding_stmt!r} anchor did not give one segment")
        elif e.get("extent") == "section":
            off = min(starts) if starts else (stmt_offsets.get(binding_stmt) or (ctx.unit_ranges[0] if ctx.unit_ranges else (None,)))[0]
            seg = ctx.section_of(off) if (ctx.section_of and off is not None) else None
            if seg is None:
                rep.problems.append(f"entities[{i}] {r!r}: no section for extent 'section'")
        if seg is not None:
            e["scope_segment"] = seg
    return out, rep


def _statement_scope(keys: list[str], ctx: UnitContext) -> str | None:
    if ctx.statement_scope is not None:
        return ctx.statement_scope(keys)
    return keys[0] if len(keys) == 1 else None


# ============================================================================ re-anchoring


def reanchor(stored: dict, old_text: str, new_ctx: UnitContext) -> tuple[dict, list[str]]:
    """Move a stored batch's spans from rendition text ``old_text`` to ``new_ctx`` (instruments §3).

    Each span's text is taken from the old rendition and located in the new unit (tiers 2-3),
    then fuzzily in each new sentence (tier 4, best score). Returns the new batch and the list
    of spans that failed (kept unchanged and listed)."""
    out = copy.deepcopy(stored)
    failed: list[str] = []

    def move(d: dict, loc: str):
        s, e = d.get("start"), d.get("end")
        if s is None or e is None:
            return
        quote = old_text[s:e]
        res = locate_quote(quote, None, new_ctx)
        if res.tier is None:
            best = None
            for sid, (a, b) in new_ctx.sentences.items():
                r = fuzz.partial_ratio_alignment(quote, new_ctx.text[a:b], score_cutoff=FUZZY_CUTOFF)
                if r is not None and (best is None or r.score > best[0]):
                    best = (r.score, a + r.dest_start, a + r.dest_end)
            if best is None:
                failed.append(f"{loc}: {quote!r}")
                return
            d["start"], d["end"] = best[1], best[2]
        else:
            d["start"], d["end"] = res.start, res.end
        if "text" in d and not d.get("coarse"):
            d["text"] = new_ctx.text[d["start"] : d["end"]]

    def walk(o, loc):
        if isinstance(o, dict):
            if "start" in o and "end" in o and isinstance(o.get("start"), int):
                move(o, loc)
            for k, v in o.items():
                walk(v, f"{loc}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{loc}[{i}]")

    walk(out, "batch")
    return out, failed


# ============================================================================ CLI


def context_from_json(cfg: dict, base: Path) -> UnitContext:
    text = cfg.get("text")
    if text is None:
        text = (base / cfg["text_path"]).read_text(encoding="utf-8")
    sections = [tuple(x) for x in cfg.get("sections", [])]
    segments = [tuple(x) for x in cfg.get("segments", [])]
    sent_keys = cfg.get("sentence_keys", {})
    key_span = {k: tuple(cfg["sentences"][sid]) for sid, k in sent_keys.items() if sid in cfg["sentences"]}
    key_span.update({k: (a, b) for a, b, k in segments})

    def section_of(off):
        best = [s for s in sections if s[0] <= off < s[1]]
        return min(best, key=lambda s: s[1] - s[0])[2] if best else None

    def statement_scope(keys):
        if len(keys) == 1:
            return keys[0]
        spans = [key_span[k] for k in keys if k in key_span]
        if not spans:
            return None
        lo, hi = min(a for a, _ in spans), max(b for _, b in spans)
        best = [s for s in segments if s[0] <= lo and hi <= s[1]]
        return min(best, key=lambda s: s[1] - s[0])[2] if best else None

    return UnitContext(
        text=text,
        unit_ranges=[tuple(r) for r in cfg["unit_ranges"]],
        sentences={k: tuple(v) for k, v in cfg["sentences"].items()},
        unit_keys=cfg.get("unit_keys", []),
        sentence_keys=sent_keys,
        section_of=section_of if sections else None,
        statement_scope=statement_scope,
        document_key=cfg.get("document_key"),
        macros=cfg.get("macros"),
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("batch")
    ap.add_argument("--context", required=True)
    ap.add_argument("--out")
    ap.add_argument("--report")
    a = ap.parse_args(argv)
    env, batch = load_batch(a.batch)
    cpath = Path(a.context)
    ctx = context_from_json(json.loads(cpath.read_text(encoding="utf-8")), cpath.parent)
    stored, rep = to_stored(batch, ctx)
    if env is not None:
        stored = {"envelope": {**env, "form": "stored"}, "batch": stored}
    text = json.dumps(stored, ensure_ascii=False, indent=2)
    if a.out:
        Path(a.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    if a.report:
        Path(a.report).write_text(json.dumps(rep.as_json(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"by_tier": rep.by_tier(), "problems": rep.problems}, ensure_ascii=False), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
