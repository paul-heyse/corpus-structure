"""Domain working projections of retained primary linguistic nodes; no recognition."""

from __future__ import annotations

from corpus_structure.semantic.constructions.retained_rules import (
    PREDICATE_FRAME_VERSION as PREDICATE_FRAME_VERSION,
)
from corpus_structure.semantic.constructions.retained_rules import (
    PRIMARY_RULE_FAMILY,
    PRIMARY_RULE_VOCABULARY,
)
from corpus_structure.semantic.constructions.retained_rules import (
    FrameCue as FrameCue,
)
from corpus_structure.semantic.constructions.retained_rules import (
    FrameIssue as FrameIssue,
)
from corpus_structure.semantic.constructions.retained_rules import (
    FrameLayout as FrameLayout,
)
from corpus_structure.semantic.constructions.retained_rules import (
    FrameRole as FrameRole,
)
from corpus_structure.semantic.constructions.retained_rules import (
    LocatedFrameSpan as LocatedFrameSpan,
)
from corpus_structure.semantic.constructions.retained_rules import (
    PredicateFrame as PredicateFrame,
)
from corpus_structure.semantic.constructions.retained_rules import (
    PredicateFrameResult as PredicateFrameResult,
)
from corpus_structure.semantic.constructions.retained_rules import (
    RoleSpan as RoleSpan,
)
from corpus_structure.semantic.constructions.retained_rules import (
    _frame_vocabulary as _frame_vocabulary,
)
from corpus_structure.semantic.constructions.retained_rules import (
    interpretation_recipe as interpretation_recipe,
)


def _reports(product):
    layers = getattr(product, "primary_layers", None)
    if not layers:
        raise ValueError("predicate consumer requires exact retained primary construction layers")
    selected = [
        (pin, report)
        for pin, report in layers.items()
        if PRIMARY_RULE_FAMILY in report.payload["operation"]["produced_families"]
    ]
    if not selected:
        raise ValueError("retained primary source-reading family is missing")
    return selected


def _span(product, text, term, occurrences):
    extents = tuple(
        (e["start"], e["end"])
        for oid in term.get("occurrences", ())
        for e in occurrences[oid]["extents"]
    )
    if any(not product.block_start <= a < b <= product.block_end for a, b in extents):
        raise ValueError("retained primary member lies outside its native block")
    indices = tuple(
        index
        for index, token in enumerate(product.tokens)
        if not text[token.start : token.end].isspace()
        and any(a <= token.start < token.end <= b for a, b in extents)
    )
    if extents and not indices:
        raise ValueError("retained primary member has no exact canonical token correspondence")
    return LocatedFrameSpan(indices, extents)


def source_layout(product, text, pieces, items):
    """Read the producer's structural-context interpretation without heading matching."""
    try:
        for _pin, report in _reports(product):
            terms = {t["local_id"]: t for t in report.payload["terms"]}
            for term in terms.values():
                if term.get("vocabulary") != PRIMARY_RULE_VOCABULARY or term["kind"] != "predicate":
                    continue
                members = {
                    edge["role"]: terms[edge["target"]]
                    for edge in term.get("children", ())
                    if "target" in edge
                }
                if "predicate" not in members:
                    continue
                occurrences = {o["local_id"]: o for o in report.payload["occurrences"]}
                try:
                    _span(product, text, members["predicate"], occurrences)
                except ValueError:
                    continue
                for edge in term.get("children", ()):
                    if edge["role"] == "layout" and edge.get("target") in terms:
                        value = terms[edge["target"]]["value"]
                        if value in {"prose", "example", "policy", "instruction"}:
                            return value
    except ValueError:
        pass
    return "unknown"


def predicate_frames(text, annotations, *, layout="prose"):
    frames, issues, unresolved = [], [], []
    for product in annotations:
        available = {
            column.attribute for column in product.availability if column.status == "complete"
        }
        missing = sorted({"DEP", "POS", "SENT_START"} - available)
        if missing:
            issues.append(
                FrameIssue(
                    product.block_id,
                    product.dependency_digest,
                    "unavailable",
                    "required retained columns: " + ", ".join(missing),
                )
            )
            continue
        from hashlib import sha256

        if (
            not 0 <= product.block_start < product.block_end <= len(text)
            or sha256(text[product.block_start : product.block_end].encode()).hexdigest()
            != product.text_digest
        ):
            issues.append(
                FrameIssue(
                    product.block_id,
                    product.dependency_digest,
                    "unsupported_alignment",
                    "retained native block differs from exact source text",
                )
            )
            continue
        try:
            result = _project(text, product)
        except (ValueError, KeyError, IndexError) as error:
            issues.append(
                FrameIssue(product.block_id, product.dependency_digest, "unavailable", str(error))
            )
            continue
        frames.extend(result.frames)
        issues.extend(result.issues)
        unresolved.extend(result.unresolved_cues)
    return PredicateFrameResult(tuple(frames), tuple(issues), tuple(unresolved))


def frames_from_annotation(view, *, layout="prose"):
    return predicate_frame_result(view, layout=layout).frames


def predicate_frame_result(view, *, layout="prose"):
    """Restore native text only to project exact retained positions; never match a rule."""
    view.check_layout()
    text = " " * view.product.block_start + view.doc.text
    return predicate_frames(text, (view.product,), layout=layout)


def _project(text, product):
    from corpus_structure.semantic.characterization import annotation_reference

    frames, issues, unresolved = [], [], []
    for pin, report in _reports(product):
        body = report.payload
        for coverage in body["coverage"]:
            if coverage["family"] == PRIMARY_RULE_FAMILY and coverage["outcome"] not in {
                "complete",
                "empty",
            }:
                issues.append(
                    FrameIssue(
                        product.block_id,
                        product.dependency_digest,
                        "unavailable",
                        coverage.get("reason", "primary family incomplete"),
                    )
                )
        terms = {t["local_id"]: t for t in body["terms"]}
        annotations = {a["local_id"]: a for a in body["annotations"]}
        occurrences = {o["local_id"]: o for o in body["occurrences"]}

        def edges(term, *, terms=terms):
            return {
                edge["role"]: terms[edge["target"]]
                for edge in term.get("children", ())
                if "target" in edge
            }

        selected = {}
        for term in terms.values():
            if term.get("vocabulary") != PRIMARY_RULE_VOCABULARY or term["kind"] != "predicate":
                continue
            members = edges(term)
            if "predicate" not in members or "focus" not in members:
                continue
            try:
                predicate = _span(product, text, members["predicate"], occurrences)
                focus = _span(product, text, members["focus"], occurrences)
            except ValueError:
                continue
            if not predicate.tokens:
                continue
            source = next(
                (
                    annotations[p]
                    for p in term.get("premises", ())
                    if p in annotations
                    and annotations[p].get("vocabulary") == PRIMARY_RULE_VOCABULARY
                ),
                None,
            )
            if source is None:
                raise ValueError("retained primary predication lacks its construction premise")
            roles = []
            for edge in term.get("children", ()):
                if (
                    edge["role"]
                    in {
                        "predicate",
                        "focus",
                        "voice",
                        "polarity",
                        "interpretation",
                        "layout",
                        "clause_role",
                    }
                    or "target" not in edge
                ):
                    continue
                member = terms[edge["target"]]
                span = _span(product, text, member, occurrences)
                own = edges(member)
                head = (
                    _span(product, text, own["head"], occurrences).tokens[0]
                    if "head" in own
                    else span.tokens[0]
                    if span.tokens
                    else predicate.tokens[0]
                )
                inherited = (
                    _span(product, text, own["inherited_from"], occurrences).tokens[0]
                    if "inherited_from" in own
                    else None
                )

                roles.append(
                    FrameRole(
                        edge["role"],
                        head,
                        span,
                        "located" if member["status"] == "interpreted" else "unresolved",
                        inherited,
                        annotation_reference(pin, member["local_id"]),
                    )
                )
            sentence = product.tokens[predicate.tokens[0]].sentence
            if sentence is None:
                raise ValueError("retained predication lacks native sentence correspondence")
            selected[term["local_id"]] = PredicateFrame(
                product.block_id,
                product.dependency_digest,
                sentence,
                predicate,
                focus,
                term["value"],
                source["native_label"],
                tuple(roles),
                (),
                members["voice"]["value"],
                members["polarity"]["value"],
                members["interpretation"]["value"],
                annotation_reference(pin, term["local_id"]),
                members.get("clause_role", {}).get("value", "unresolved"),
            )
        cues = {}
        for term in terms.values():
            if term.get("vocabulary") != PRIMARY_RULE_VOCABULARY or term["kind"] != "operator":
                continue
            members = edges(term)
            if "cue" not in members or "basis" not in members:
                continue
            try:
                span = _span(product, text, members["cue"], occurrences)
                basis = _span(product, text, members["basis"], occurrences)
            except ValueError:
                continue
            source = next(
                (annotations[p] for p in term.get("premises", ()) if p in annotations), None
            )
            if source is None:
                raise ValueError("retained cue lacks its construction premise")
            hosts = tuple(
                selected[r["member"]].predicate.tokens[0]
                for r in body["roles"]
                if r["owner"] == term["local_id"]
                and r["role"] == "host"
                and r["member"] in selected
            )
            origin = (
                _span(product, text, members["origin"], occurrences).tokens[0]
                if "origin" in members
                else None
            )
            component = (
                _span(product, text, members["component"], occurrences).tokens[0]
                if "component" in members
                else None
            )
            cue = FrameCue(
                product.block_id,
                product.dependency_digest,
                term["value"],
                source["native_label"],
                span,
                basis,
                "located" if term["status"] == "interpreted" else "unresolved",
                hosts,
                origin,
                component,
                annotation_reference(pin, term["local_id"]),
                annotation_reference(pin, members["basis"]["local_id"]),
            )
            cues[term["local_id"]] = cue
            if not hosts:
                unresolved.append(cue)
        from dataclasses import replace

        for key, frame in selected.items():
            hosted = tuple(
                cues[r["owner"]]
                for r in body["roles"]
                if r["role"] == "host" and r["member"] == key and r["owner"] in cues
            )
            frames.append(replace(frame, cues=hosted))
    return PredicateFrameResult(tuple(frames), tuple(issues), tuple(unresolved))
