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
``sections`` (``[[start, end, key], ...]``) and ``segments`` (``[[start, end, key], ...]``,
any non-sentence segments, used for the default ``statement_scope``).

Tiers (recorded on every result): 1 exact in the cited sentence; 2 exact in the unit; 3 exact
after normalization (math delimiters ``$``/``$$``/``\\(\\)``/``\\[\\]`` and spacing commands
``\\,`` ``\\;`` ``\\!`` dropped, all whitespace removed) with an offset map, cited sentence
then unit; 4 ``rapidfuzz.fuzz.partial_ratio_alignment(quote, sentence, score_cutoff=95)``
within the cited sentence (quotes over 64 characters flagged). Unlocated: the cited sentence's
span with ``coarse: true``; without a valid cited sentence the item is dropped as malformed.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

from rapidfuzz import fuzz

sys.path.insert(0, str(Path(__file__).resolve().parent))

from instruments.batch import load_batch  # noqa: E402
from instruments.conditions import as_dict, entity_positions, formula_positions  # noqa: E402

FUZZY_CUTOFF = 95
FUZZY_OPTIMAL_MAX = 64  # RapidFuzz: partial_ratio is optimal only up to 64 chars of the shorter string


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

    def sentence_span(self, sid):
        return self.sentences.get(sid) if sid is not None else None


@dataclass
class Located:
    start: int | None
    end: int | None
    tier: int | None  # 1-4, None when unlocated
    scope: str | None = None  # sentence | unit
    matches: int = 0  # exact (or normalized) matches at the deciding tier; >1 = ambiguous
    score: float | None = None
    long_quote: bool = False
    coarse: bool = False
    dropped: bool = False
    note: str = ""


def _occurrences(hay: str, needle: str, base: int) -> list[int]:
    out, i = [], hay.find(needle)
    while i >= 0:
        out.append(base + i)
        i = hay.find(needle, i + 1)
    return out


_OPEN = ("\\(", "\\[")
_CLOSE = ("\\)", "\\]")
_SPACING = ("\\,", "\\;", "\\!")


def normalize(s: str, dollars: bool) -> tuple[str, list[int]]:
    """Normalized string and, per normalized character, its index in ``s``."""
    out, idx = [], []
    i, n = 0, len(s)
    while i < n:
        two = s[i : i + 2]
        if two in _OPEN or two in _CLOSE or two in _SPACING:
            i += 2
            continue
        if dollars and s[i] == "$":
            i += 2 if two == "$$" else 1
            continue
        if s[i].isspace():
            i += 1
            continue
        out.append(s[i])
        idx.append(i)
        i += 1
    return "".join(out), idx


def _extend_delims(text: str, start: int, end: int, quote: str) -> tuple[int, int]:
    q = quote.strip()
    if q.startswith(("$", "\\(", "\\[")):
        j = start
        while j > 0 and text[j - 1].isspace():
            j -= 1
        if text[max(0, j - 2) : j] in _OPEN:
            start = j - 2
    if q.endswith(("$", "\\)", "\\]")):
        j = end
        while j < len(text) and text[j].isspace():
            j += 1
        if text[j : j + 2] in _CLOSE:
            end = j + 2
    return start, end


def _norm_find(text: str, lo: int, hi: int, quote: str) -> list[tuple[int, int]]:
    hay, idx = normalize(text[lo:hi], dollars=False)
    nq, _ = normalize(quote, dollars=True)
    if not nq:
        return []
    out = []
    i = hay.find(nq)
    while i >= 0:
        s, e = lo + idx[i], lo + idx[i + len(nq) - 1] + 1
        out.append(_extend_delims(text, s, e, quote))
        i = hay.find(nq, i + 1)
    return out


def locate_quote(quote: str, sentence: str | None, ctx: UnitContext) -> Located:
    """D4 §4.3 step 2 for one quote cited in ``sentence`` (an id, or None)."""
    text = ctx.text
    sent = ctx.sentence_span(sentence)
    long_q = len(quote) > FUZZY_OPTIMAL_MAX
    if not quote.strip():
        return Located(*(sent or (None, None)), None, coarse=sent is not None, dropped=sent is None, note="empty quote")
    # 1 exact in the cited sentence
    if sent:
        occ = _occurrences(text[sent[0] : sent[1]], quote, sent[0])
        if occ:
            return Located(occ[0], occ[0] + len(quote), 1, "sentence", len(occ), long_quote=long_q)
    # 2 exact in the unit (nearest occurrence to the cited sentence when several)
    occ = [o for lo, hi in ctx.unit_ranges for o in _occurrences(text[lo:hi], quote, lo) if o + len(quote) <= hi]
    if occ:
        anchor = sent[0] if sent else ctx.unit_ranges[0][0]
        best = min(occ, key=lambda o: (abs(o - anchor), o))
        return Located(best, best + len(quote), 2, "unit", len(occ), long_quote=long_q)
    # 3 normalized, sentence then unit
    if sent:
        hits = _norm_find(text, sent[0], sent[1], quote)
        if hits:
            return Located(hits[0][0], hits[0][1], 3, "sentence", len(hits), long_quote=long_q)
    hits = [h for lo, hi in ctx.unit_ranges for h in _norm_find(text, lo, hi, quote)]
    if hits:
        anchor = sent[0] if sent else ctx.unit_ranges[0][0]
        best = min(hits, key=lambda h: (abs(h[0] - anchor), h[0]))
        return Located(best[0], best[1], 3, "unit", len(hits), long_quote=long_q)
    # 4 fuzzy within the cited sentence
    if sent:
        r = fuzz.partial_ratio_alignment(quote, text[sent[0] : sent[1]], score_cutoff=FUZZY_CUTOFF)
        if r is not None:
            return Located(sent[0] + r.dest_start, sent[0] + r.dest_end, 4, "sentence", 1, r.score, long_q)
        return Located(sent[0], sent[1], None, coarse=True, long_quote=long_q, note="unlocated; cited sentence span")
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
            k = "dropped" if r.result.dropped else ("coarse" if r.result.coarse else f"tier{r.result.tier}")
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
