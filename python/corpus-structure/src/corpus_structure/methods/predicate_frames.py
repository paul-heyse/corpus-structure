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


class PreparedPredicateReadings:
    """One invocation-owned index of supplied immutable primary inventories."""
    def __init__(self, products):
        import json
        from corpus_structure.semantic.data_product_reference import DataProductReference
        from corpus_structure.semantic.data_operation_model import json_context_meaning
        from corpus_structure.semantic.identity import canonical_bytes

        self.products = tuple(products)
        self.inventories = tuple((
            DataProductReference(product.semantic_id),
            body["source"],
            json_context_meaning(canonical_bytes({"source": body["source"], "selectors": body["selectors"]})).decode(),
            {**product.inventory(), "coverage": body["coverage"]},
        ) for product in self.products for body in (json.loads(product.content),))

    def __iter__(self):
        return iter(self.products)

    def __len__(self):
        return len(self.products)


def prepare_predicate_readings(products):
    return products if isinstance(products, PreparedPredicateReadings) else PreparedPredicateReadings(products)


def _reports(product, primary_products=()):
    """Read explicit governed inventories, or the genuine sealed historical layers."""
    if primary_products:
        from corpus_structure.semantic.declared_record_sources import DeclaredSourcePin

        if not isinstance(product.source, DeclaredSourcePin):
            raise ValueError("declared predicate input requires its original governed source pin")
        source = product.source.values()
        selected = []
        for pin, coordinate, scope, inventory in prepare_predicate_readings(primary_products).inventories:
            if (coordinate["document"] != source["original_source"]
                or coordinate["projection"] != source["projection_digest"]
                or scope != source["analyzed_scope_meaning"]):
                raise ValueError("predicate primary product differs from its exact original source")
            if any(row["family"] == PRIMARY_RULE_FAMILY for row in inventory["coverage"]):
                selected.append((pin, inventory))
    else:
        layers = getattr(product, "primary_layers", None)
        if not layers:
            raise ValueError("predicate consumer requires exact retained primary construction products")
        selected = [(pin, report.payload) for pin, report in layers.items() if PRIMARY_RULE_FAMILY in report.payload["operation"]["produced_families"]]
    if not selected:
        raise ValueError("retained primary source-reading family is missing")
    return selected


def primary_inventory(product, reference, *, primary_products=()):
    matches = [body for pin, body in _reports(product, primary_products) if pin == reference.product]
    if len(matches) != 1:
        raise ValueError("predicate reference lacks one exact primary product inventory")
    return matches[0]


def _projection(product):
    from corpus_structure.semantic.declared_record_sources import DeclaredSourcePin
    return product.source.values()["projection_digest"] if isinstance(product.source, DeclaredSourcePin) else product.source.projection_digest


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


def source_layout(product, text, pieces, items, *, primary_products=()):
    """Read the producer's structural-context interpretation without heading matching."""
    try:
        for _pin, body in _reports(product, primary_products):
            terms = {t["local_id"]: t for t in body["terms"]}
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
                occurrences = {o["local_id"]: o for o in body["occurrences"]}
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


def predicate_frames(text, annotations, *, layout="prose", primary_products=()):
    primary_products = prepare_predicate_readings(primary_products) if primary_products else ()
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
            result = _project(text, product, primary_products=primary_products)
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


def _project(text, product, *, primary_products=()):
    from corpus_structure.semantic.data_product_reference import member_reference

    frames, issues, unresolved = [], [], []
    for pin, body in _reports(product, primary_products):
        for coverage in body["coverage"]:
            if coverage["family"] != PRIMARY_RULE_FAMILY:
                continue
            examined = coverage["availability"] == "available" and any(
                selector.get("projection") == _projection(product)
                and selector.get("start", 0) <= product.block_start
                and selector.get("end", len(text)) >= product.block_end
                for selector in coverage.get("examined", ())
            )
            unexamined = any(
                selector.get("projection") == _projection(product)
                and selector.get("start", 0) < product.block_end
                and selector.get("end", len(text)) > product.block_start
                for selector in coverage.get("unexamined", ())
            )
            if not examined or unexamined:
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
                        "negation_examination",
                        "modality_examination",
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
                        member_reference(pin, member["local_id"]),
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
                member_reference(pin, term["local_id"]),
                members.get("clause_role", {}).get("value", "unresolved"),
                members.get("negation_examination", {}).get("value") == "complete",
                members.get("modality_examination", {}).get("value") == "complete",
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
                member_reference(pin, term["local_id"]),
                member_reference(pin, members["basis"]["local_id"]),
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
