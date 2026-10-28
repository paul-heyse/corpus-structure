"""M13 binding sites as spaCy Matcher patterns over b′ documents (ADR-0009, revisit S0-R1).

The patterns are generated from the pack's binder lexicon (D2 §12.1 `binders`): nothing here names
a source or a sentence. Each merged inline-math token carries `Token._.math`, set by a classifier
(the math grammar) to {"kind": symbol|member|equation|relation|expression|other, "symbols": [...],
"bound": [...]} where `bound` lists the symbols the math itself introduces (a lone symbol, the left
side of a membership, the left side of an equation whose left side is one symbol, the left side
of a restriction).

A binding site is a math token whose `bound` symbols are introduced by one of:
  initial     a sentence whose first word is in `sentence_initial` ("Suppose", "Let", "If", …)
  clause      a math token directly after a `clause` binder ("where", "for")
  definition  an equation whose left side is one symbol, anywhere (`W = e^Z`)
Sentence-level flags: `section_wide` phrases make the binding section-wide; `reopen` words
("again") re-open the section's earlier binding.
"""

from __future__ import annotations

from typing import Callable

from spacy.matcher import Matcher
from spacy.tokens import Doc, Token

if not Token.has_extension("math"):
    Token.set_extension("math", default=None)
if not Token.has_extension("is_math"):
    Token.set_extension("is_math", getter=lambda t: t._.math is not None)


def build_matcher(nlp, lexicon: dict) -> Matcher:
    m = Matcher(nlp.vocab, validate=True)
    m.add("INITIAL", [[{"IS_SENT_START": True, "LOWER": {"IN": [w.lower() for w in lexicon["sentence_initial"]]}}]])
    m.add("CLAUSE", [[{"LOWER": {"IN": [w.lower() for w in lexicon["clause"]]}}, {"_": {"is_math": True}}]])
    m.add("REOPEN", [[{"LOWER": {"IN": [w.lower() for w in lexicon.get("reopen", [])]}}]])
    for phrase in lexicon.get("section_wide", []):
        m.add("SECTION_WIDE", [[{"LOWER": w} for w in phrase.lower().split()]])
    return m


def annotate(doc: Doc, block_start: int, text: str, classify: Callable[[str], dict]) -> Doc:
    """Set `_.math` on every merged inline-math token (offsets in canonical text)."""
    for t in doc:
        s = t.text
        if s.startswith("\\(") and s.endswith("\\)") or s.startswith("\\[") and s.endswith("\\]"):
            info = dict(classify(s))
            info["start"], info["end"] = block_start + t.idx, block_start + t.idx + len(s)
            t._.math = info
    return doc


def binding_sites(doc: Doc, matcher: Matcher) -> list[dict]:
    """Binding sites in a b′ document whose math tokens carry `_.math`."""
    flags: dict[int, set[str]] = {}
    clause_tokens: set[int] = set()
    for mid, start, end in matcher(doc):
        rule = doc.vocab.strings[mid]
        sent = doc[start].sent
        flags.setdefault(sent.start, set()).add(rule)
        if rule == "CLAUSE":
            clause_tokens.add(end - 1)
    sites = []
    for sent in doc.sents:
        f = flags.get(sent.start, set())
        for t in sent:
            info = t._.math
            if not info or not info.get("bound"):
                continue
            rules = []
            if "INITIAL" in f:
                rules.append("initial")
            if t.i in clause_tokens:
                rules.append("clause")
            if info.get("kind") == "equation":
                rules.append("definition")
            if not rules:
                continue
            sites.append({"symbols": list(info["bound"]), "start": info["start"], "end": info["end"],
                          "rules": rules, "section_wide": "SECTION_WIDE" in f, "reopen": "REOPEN" in f,
                          "sentence": (sent.start_char, sent.end_char)})
    return sites
