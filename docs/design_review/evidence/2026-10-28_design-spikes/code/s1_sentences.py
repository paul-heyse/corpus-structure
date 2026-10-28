"""S1 sentence segmentation (M03 prototype): spaCy pipelines × math handling.

Pipelines: P1 en_core_web_sm parser, P2 en_core_web_sm senter, P3 rule sentencizer, P4 en_core_web_trf.
Math handling: a raw; b1 inline math masked as an opaque placeholder; b2 masked as a word-like
token; bp (b′) inline math merged into one token before the parser (offsets stay in canonical text);
d inline math rendered to Unicode with pylatexenc 3.0b2 latex2text (plain-text settings). Suffix "+c" adds the rule that
no boundary falls inside display math or at a rendered reference marker. Sentences never cross their block (blocks are split
separately). Plan: docs/plans/design-spikes-s0-s1/S1-ingest-segmentation.md §6.
"""

from __future__ import annotations

import functools
import re

import spacy
from pylatexenc.latex2text import LatexNodes2Text
from s1_adapter import make_key
from spacy.language import Language

SPLIT_KINDS = {"paragraph", "list_item", "table_cell", "caption"}
PIPELINES = {
    "P1": ("en_core_web_sm", "parser"),
    "P2": ("en_core_web_sm", "senter"),
    "P3": (None, "sentencizer"),
    "P4": ("en_core_web_trf", "parser"),
}


@functools.cache
def pipeline(name: str) -> Language:
    model, mode = PIPELINES[name]
    if model is None:
        nlp = spacy.blank("en")
        nlp.add_pipe("sentencizer")
        return nlp
    if mode == "senter":
        nlp = spacy.load(model, disable=["parser"])
        nlp.enable_pipe("senter")
        return nlp
    return spacy.load(model)


def blocks_of(rendition: dict) -> list[dict]:
    segs = rendition["segments"]
    kids: dict[str | None, list[dict]] = {}
    for s in segs:
        kids.setdefault(s["parent"], []).append(s)
    out = []
    for s in segs:
        if s["kind"] in SPLIT_KINDS:
            math = [{"start": m["start"] - s["start"], "end": m["end"] - s["start"], "display": m["kind"] == "math_display"}
                    for m in kids.get(s["key"], []) if m["kind"].startswith("math")]
            refs = [{"start": r["start"] - s["start"], "end": r["end"] - s["start"]}
                    for r in rendition["markup"] if r["markup"] == "aref" and r.get("segment") == s["key"]
                    and r["end"] > r["start"]]
            out.append({"key": s["key"], "kind": s["kind"], "start": s["start"],
                        "text": rendition["text"][s["start"]:s["end"]], "math": sorted(math, key=lambda m: m["start"]),
                        "refs": refs})
    return out


# ---------------------------------------------------------------------------- math presentations

def masked(block: dict, form: str) -> tuple[str, list[tuple[int, int, int, int]]]:
    """Replace inline math; returns new text and a list of (orig_start, orig_end, new_start, new_end)."""
    text, parts, spans = block["text"], [], []
    pos = 0
    n = 0
    for m in block["math"]:
        if m["display"]:
            continue
        parts.append(text[pos:m["start"]])
        new_start = sum(len(p) for p in parts)
        n += 1
        token = {"b1": f"⟨m{n}⟩", "b2": f"MATHTOKEN{n}"}[form]
        parts.append(token)
        spans.append((m["start"], m["end"], new_start, new_start + len(token)))
        pos = m["end"]
    parts.append(text[pos:])
    return "".join(parts), spans


@functools.cache
def _l2t() -> LatexNodes2Text:
    return LatexNodes2Text(math_mode="text", math_fontstyle=None, text_fontstyle=False)  # v2-like plain text


def rendered(block: dict, macros: dict) -> tuple[str, list[tuple[int, int, int, int]]]:
    text, parts, spans = block["text"], [], []
    pos = 0
    for m in block["math"]:
        if m["display"]:
            continue
        tex = text[m["start"]:m["end"]]
        inner = tex[2:-2] if tex.startswith("\\(") and tex.endswith("\\)") else tex
        for name, d in sorted(macros.items(), key=lambda kv: -len(kv[0])):
            if d["nargs"] == 0:
                inner = re.sub(re.escape(name) + r"(?![A-Za-z])", lambda _m, b=d["body"]: b, inner)
        try:
            uni = _l2t().latex_to_text(inner).strip() or "x"
        except Exception:
            uni = "x"
        parts.append(text[pos:m["start"]])
        new_start = sum(len(p) for p in parts)
        parts.append(uni)
        spans.append((m["start"], m["end"], new_start, new_start + len(uni)))
        pos = m["end"]
    parts.append(text[pos:])
    return "".join(parts), spans


def back(offset: int, spans: list[tuple[int, int, int, int]]) -> int:
    """Map an offset in the replaced text back to the original block text."""
    shift = 0
    for os_, oe, ns, ne in spans:
        if offset < ns:
            break
        if offset < ne:  # inside a replacement: snap to the original span start
            return os_
        shift = oe - ne
    return offset + shift


# ---------------------------------------------------------------------------- splitting

def split_block(block: dict, pipe: str, math: str, macros: dict) -> list[int]:
    """Sentence start offsets (relative to the block, excluding 0)."""
    nlp = pipeline(pipe)
    base, rule_c = math.split("+")[0], math.endswith("+c")
    if base == "bp":
        starts = _split_merged(nlp, block)
    else:
        if base == "a":
            text, spans = block["text"], []
        elif base in ("b1", "b2"):
            text, spans = masked(block, base)
        elif base == "d":
            text, spans = rendered(block, macros)
        else:
            raise ValueError(math)
        doc = nlp(text)
        starts = [back(s.start_char, spans) for s in doc.sents][1:]
    if rule_c:  # no boundary inside display math, and none at a rendered reference marker ("[14]")
        disp = [(m["start"], m["end"]) for m in block["math"] if m["display"]]
        refs = [(r["start"], r["end"]) for r in block.get("refs", [])]
        starts = [s for s in starts if not any(a < s < e for a, e in disp) and not any(a <= s < e for a, e in refs)]
    return sorted({s for s in starts if 0 < s < len(block["text"])})


def _split_merged(nlp: Language, block: dict) -> list[int]:
    """b′: merge each inline math span into one token (POS PROPN) and forbid starts inside display math,
    before the statistical components run; offsets stay those of the canonical text."""
    doc = nlp.make_doc(block["text"])
    with doc.retokenize() as rt:
        for m in block["math"]:
            if m["display"]:
                continue
            span = doc.char_span(m["start"], m["end"], alignment_mode="expand")
            if span is not None and len(span) > 1:
                rt.merge(span, attrs={"POS": "PROPN", "TAG": "NNP"})
        for r in block.get("refs", []):  # rendered reference markers are one token, never a sentence start
            span = doc.char_span(r["start"], r["end"], alignment_mode="expand")
            if span is not None and len(span) > 1:
                rt.merge(span, attrs={"POS": "PROPN", "TAG": "NNP"})
    for r in block.get("refs", []):
        span = doc.char_span(r["start"], r["end"], alignment_mode="expand")
        if span is not None:
            for t in span:
                t.is_sent_start = False
    for m in block["math"]:
        if not m["display"]:
            continue
        span = doc.char_span(m["start"], m["end"], alignment_mode="expand")
        if span is not None:
            for t in span[1:]:
                t.is_sent_start = False
    for _, proc in nlp.pipeline:
        doc = proc(doc)
    return [s.start_char for s in doc.sents][1:]


def sentences(rendition: dict, pipe: str, math: str) -> list[dict]:
    """Sentence segments (D1 §3.2 kind `sentence`) for every splittable block of a rendition."""
    macros = rendition["rendition"]["parse_detail"]["macros"]
    ren = rendition["rendition"]["rendition_key"]
    out = []
    for b in blocks_of(rendition):
        cuts = [0, *split_block(b, pipe, math, macros), len(b["text"])]
        for a, e in zip(cuts, cuts[1:], strict=False):
            sa, se = a, e
            while sa < se and b["text"][sa].isspace():
                sa += 1
            while se > sa and b["text"][se - 1].isspace():
                se -= 1
            if se > sa:
                start, end = b["start"] + sa, b["start"] + se
                out.append({"key": make_key("seg", [ren, "sentence", start, end]), "kind": "sentence",
                            "start": start, "end": end, "parent": b["key"]})
    return out
