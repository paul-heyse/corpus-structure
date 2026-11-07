"""Located procedure roles from retained dependency columns, without reparsing text.

These are linguistic proposals. Voice, coordination, negation and clause markers
are retained as evidence; grammatical roles never authorize semantic publication.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal, TypedDict

from .predicate_frames import (
    PREDICATE_FRAME_VERSION as PREDICATE_FRAME_VERSION,
)
from .predicate_frames import (
    FrameCue as FrameCue,
)
from .predicate_frames import (
    PredicateFrame as PredicateFrame,
)
from .predicate_frames import (
    frames_from_annotation as frames_from_annotation,
)
from .predicate_frames import (
    predicate_frame_result as predicate_frame_result,
)
from .predicate_frames import (
    predicate_frames as predicate_frames,
)

type RoleSpan = tuple[int, int]


class ProcedureFrame(TypedDict):
    action: RoleSpan
    actor: tuple[RoleSpan, ...]
    object: tuple[RoleSpan, ...]
    modality: tuple[RoleSpan, ...]
    conditions: list[RoleSpan]
    exceptions: list[RoleSpan]
    orders: list[tuple[RoleSpan, RoleSpan]]
    voice: Literal["active", "passive"]
    polarity: Literal["positive", "negative", "negative_scope_unresolved"]
    behavior: Literal["prescribed", "example", "described_or_example_unresolved"]
    clause_role: Literal["subordinate", "main_or_coordinate"]
    dependency: str


def procedure_frames(text, annotations) -> tuple[ProcedureFrame, ...]:
    frames = []
    for product in annotations:
        available = {a.attribute for a in product.availability if a.status == "complete"}
        if not {"DEP", "POS"} <= available:
            continue
        tokens = product.tokens
        children = {i: [] for i in range(len(tokens))}
        for i, t in enumerate(tokens):
            if 0 <= t.head < len(tokens) and t.head != i:
                children[t.head].append(i)

        def descendants(i, *, nominal=False, children=children, tokens=tokens):
            result = set()
            pending = [i]
            while pending:
                current = pending.pop()
                if current in result:
                    continue
                result.add(current)
                pending.extend(
                    c
                    for c in children[current]
                    if not nominal
                    or tokens[c].dependency
                    in {"det", "amod", "compound", "nummod", "poss", "case", "flat"}
                )
            return result

        def span(indices, tokens=tokens):
            selected = [
                tokens[i] for i in indices if tokens[i].role != "math" and not tokens[i].space
            ]
            if not selected:
                return None
            a, b = min(t.start for t in selected), max(t.end for t in selected)
            if not 0 <= a < b <= len(text):
                return None
            return (a, b)

        verbs = {
            i
            for i, t in enumerate(tokens)
            if t.pos == "VERB"
            and t.dependency not in {"aux", "auxpass", "aux:pass"}
            and t.role == "prose"
        }

        def roles(i, tokens=tokens, children=children):
            passive = any(
                tokens[c].dependency
                in {"nsubjpass", "csubjpass", "nsubj:pass", "auxpass", "aux:pass"}
                for c in children[i]
            )
            actor = []
            objects = []
            for c in children[i]:
                dep = tokens[c].dependency
                if dep in {"nsubj", "csubj"}:
                    actor.append(c)
                elif dep in {"nsubjpass", "csubjpass", "nsubj:pass", "obj", "dobj", "iobj", "attr"}:
                    objects.append(c)
                elif dep in {"agent", "obl:agent"}:
                    agent = [x for x in children[c] if tokens[x].dependency in {"pobj", "obj"}]
                    actor.extend(agent or ([c] if dep == "obl:agent" else []))
            return passive, actor, objects

        basic = {i: roles(i) for i in verbs}
        # A coordinated participle can share the actual passive construction.
        # An explicit active subject or a non-participle never inherits that voice.
        for i in sorted(verbs):
            token = tokens[i]
            if (
                token.dependency == "conj"
                and token.head in basic
                and basic[token.head][0]
                and token.tag == "VBN"
                and not any(tokens[c].dependency in {"nsubj", "csubj"} for c in children[i])
            ):
                _, actor, objects = basic[i]
                basic[i] = (True, actor, objects)
        for i in sorted(verbs):
            token = tokens[i]
            passive, actor, objects = basic[i]
            peers = {i}
            if token.dependency == "conj" and token.head in verbs:
                peers.add(token.head)
            peers.update(c for c in children[i] if c in verbs and tokens[c].dependency == "conj")
            # A missing shared role is inherited only from one unambiguous same-voice
            # coordinate role source. Explicit local roles always win.
            for name, local in [("actor", actor), ("object", objects)]:
                if local:
                    continue
                candidates = {
                    x
                    for p in peers - {i}
                    if basic[p][0] == passive
                    for x in (basic[p][1] if name == "actor" else basic[p][2])
                }
                if len(candidates) == 1:
                    local.extend(candidates)
            own = children[i]
            if token.dependency == "conj" and token.head in verbs:
                own_modal = any(tokens[c].tag == "MD" for c in own)
                inherited = [
                    c
                    for c in children[token.head]
                    if tokens[c].dependency in {"aux", "auxpass", "aux:pass", "neg"}
                    and not own_modal
                ]
                own = [*own, *inherited]
            negated = any(tokens[c].dependency == "neg" for c in own)
            direct_negation = any(tokens[c].dependency == "neg" for c in children[i])
            modal = [c for c in own if tokens[c].tag == "MD"]
            behavior = (
                "prescribed"
                if any(
                    text[tokens[c].start : tokens[c].end].casefold() in {"must", "shall", "should"}
                    for c in modal
                )
                else "described_or_example_unresolved"
            )
            sentence = tokens[i].sentence
            region = [t for t in tokens if t.sentence == sentence]
            if region:
                a = min(t.start for t in region)
                b = max(t.end for t in region)
                if text[a:b].lstrip().casefold().startswith(("for example", "example ")):
                    behavior = "example"
            frame: ProcedureFrame = dict(
                action=(token.start, token.end),
                actor=tuple(s for x in actor if (s := span(descendants(x, nominal=True)))),
                object=tuple(s for x in objects if (s := span(descendants(x, nominal=True)))),
                modality=tuple((tokens[c].start, tokens[c].end) for c in modal),
                conditions=[],
                exceptions=[],
                orders=[],
                voice="passive" if passive else "active",
                polarity=("negative" if direct_negation else "negative_scope_unresolved")
                if negated
                else "positive",
                behavior=behavior,
                clause_role="subordinate" if token.dependency == "advcl" else "main_or_coordinate",
                dependency=product.dependency_digest,
            )
            for c in children[i]:
                if tokens[c].dependency != "advcl":
                    continue
                markers = [x for x in children[c] if tokens[x].dependency == "mark"]
                marker = " ".join(text[tokens[x].start : tokens[x].end].casefold() for x in markers)
                extent = span(descendants(c))
                if extent is None:
                    continue
                if marker in {"if", "when", "provided"}:
                    frame["conditions"].append(extent)
                elif marker in {"unless", "except"}:
                    frame["exceptions"].append(extent)
                elif marker in {"before", "after"} and c in verbs:
                    earlier, later = (
                        ((token.start, token.end), (tokens[c].start, tokens[c].end))
                        if marker == "before"
                        else ((tokens[c].start, tokens[c].end), (token.start, token.end))
                    )
                    frame["orders"].append((earlier, later))
            frames.append(frame)
    return tuple(frames)


@lru_cache(maxsize=1)
def _formula_syntax_context():
    from corpus_structure.semantic.analysis_contracts import prepare_interpretation_context

    return prepare_interpretation_context(macros={}, demand="syntax")


def captured_formula_symbols(text, *, seconds=0.5):
    """Consume the existing mathematical syntax owner; never create a second grammar.

    Returned offsets belong to the unchanged captured field. Failed or ambiguous
    syntax supplies no symbol-denotation link and retains an explicit diagnostic.
    """
    from corpus_structure.methods.math import grammar
    from corpus_structure.methods.math.prepared import PreparedMathInput

    context = _formula_syntax_context()
    operand = PreparedMathInput(context, text, seconds=seconds, source_text=text)
    result = operand.syntax()
    if result.tree is None or any(t.data == "_ambig" for t in result.tree.iter_subtrees()):
        if result.failure is not None and result.failure.category == "timeout":
            return (), "timeout"
        return (), "ambiguous" if result.tree is not None else "unsupported"
    occurrences = grammar.occurrences(result.tree, text, {}, frozenset())
    return tuple(
        dict(start=o.start, end=o.end, name=o.name, syntax_parent=o.in_subscript_of)
        for o in occurrences
    ), "parsed"
