"""Bounded retrieval signals projected from exact retained primary document nodes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import cached_property
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from corpus_structure.semantic.characterization import AnnotationReference, project_reading
from corpus_structure.semantic.source_contexts import (
    NativeSourceContext,
    SourceSlice,
    evidence_anchor,
    record_source_pin,
)

from .contextual_embeddings import identity
from .pm2_dipo_products import prepare_dipo_context

# Recipe-version contract, deliberately independent of recognition implementations.
PRIMARY_RULE_FAMILY = "construction.source_readings"
PRIMARY_RULE_VOCABULARY = "source-linguistic-rules-1"

ContextRecipe = Literal["located-frame-2", "located-referent-2", "located-discourse-neighbor-2"]


class QueryContextBinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    occurrence_id: str = Field(pattern=r"^source-occurrence:[0-9a-f]{64}$")
    evidence: AnnotationReference


class QueryContextSelection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    recipe: ContextRecipe
    bindings: tuple[QueryContextBinding, ...] = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def ordered_bindings(self):
        occurrences = [binding.occurrence_id for binding in self.bindings]
        if occurrences != sorted(set(occurrences)):
            raise ValueError("query context requires distinct, ordered occurrence bindings")
        return self


@dataclass(frozen=True)
class QuerySignal:
    label: str
    anchors: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True)
class LocatedQueryContext:
    recipe: ContextRecipe
    evidence: AnnotationReference
    signals: tuple[QuerySignal, ...]
    omissions: tuple[str, ...] = ()

    @property
    def rendered(self) -> str:
        return "\n".join(
            f"{signal.label}: " + " … ".join(a["source_piece"] for a in signal.anchors)
            for signal in self.signals
        )

    @property
    def representation_digest(self) -> str:
        return identity("located-query-context", self.report()) if self.signals else ""

    def report(self) -> dict:
        return {
            "recipe": self.recipe,
            "evidence": self.evidence.values(),
            "signals": [
                {"label": signal.label, "anchor_ids": [a["anchor_id"] for a in signal.anchors]}
                for signal in self.signals
            ],
            "omissions": self.omissions,
        }


class _PrimaryContext:
    def __init__(self, layer, reference, recipe, source, layers, source_context):
        self.body = layer.payload
        self.source = source
        self.source_context = source_context
        self.terms = {row["local_id"]: row for row in self.body["terms"]}
        self.annotations = {row["local_id"]: row for row in self.body["annotations"]}
        self.occurrences = {row["local_id"]: row for row in self.body["occurrences"]}
        if (
            layer.reference(reference.layer.task_id) != reference.layer
            or layer.base_document != source.native_product
            or source.source_view_id not in self.body["source_scope"]["source_view_ids"]
        ):
            raise ValueError("query context primary layer differs from its exact source or pin")
        root = (self.terms if recipe == "located-frame-2" else self.annotations).get(
            reference.local_id
        )
        if root is None:
            raise ValueError("query context primary node is absent from its exact layer")
        self.root = root
        valid = (
            self.root.get("kind") == "predicate"
            and self.root.get("family") == PRIMARY_RULE_FAMILY
            and self.root.get("vocabulary") == PRIMARY_RULE_VOCABULARY
            if recipe == "located-frame-2"
            else self.root.get("kind") == "native.coreference_cluster"
            and self.root.get("family") == "maverick.clusters"
            if recipe == "located-referent-2"
            else self.root.get("kind") in {"native.rst_node", "native.rst_singleton"}
            and self.root.get("family") == "dipo.rst"
        )
        if not valid:
            raise ValueError("query context primary node differs from selected recipe")
        if recipe == "located-frame-2":
            reading = project_reading(layer, reference.local_id, dependencies=layers)
            if reading["outcome"] != "complete":
                raise ValueError("query context requires an unambiguous retained primary reading")
        self.unconditional(self.root)

    @staticmethod
    def unconditional(row):
        # This recipe has no analytical-choice selection surface. Never silently
        # render a guarded retained fact as an unconditional observation.
        if row.get("required_choices") or row.get("required_external_choices"):
            raise ValueError("query context requires an unselected analytical choice")

    def location(self, row):
        self.unconditional(row)
        anchors = []
        for identifier in row.get("occurrences", ()):
            occurrence = self.occurrences.get(identifier)
            if occurrence is None:
                raise ValueError("query context has an unavailable primary occurrence")
            for extent in occurrence["extents"]:
                if (
                    extent.get("source_view_id") != self.source.source_view_id
                    or extent.get("projection") != self.source.projection_digest
                ):
                    raise ValueError("query context location belongs to another source projection")
                for piece in self.source_context.map_span(
                    extent["start"], extent["end"], allow_multiple=True
                ):
                    anchor, _ = evidence_anchor(self.source_context, piece, native=True)
                    if anchor not in anchors:
                        anchors.append(anchor)
        return tuple(anchors)

    def members(self, row):
        edges = sorted(
            (edge for edge in self.body["memberships"] if edge["group"] == row["local_id"]),
            key=lambda edge: (edge["order"], edge["local_id"]),
        )
        members = []
        for edge in edges:
            self.unconditional(edge)
            member = self.annotations.get(edge["member"])
            if member is None or member.get("context") != self.root.get("context"):
                raise ValueError("query context has a foreign or unavailable primary member")
            members.append(member)
        return tuple(members)

    @cached_property
    def discourse(self):
        located, splits, seen = {}, [], set()

        def visit(row):
            key = row["local_id"]
            if key in seen:
                raise ValueError("discourse context repeats a primary tree member")
            seen.add(key)
            if row["kind"] == "native.edu" and row["family"] == "dipo.edus":
                index = row["native_edu"]["index"]
                if index in located:
                    raise ValueError("discourse context repeats an EDU ordinal")
                located[index] = self.location(row)
                return index, index + 1
            if row["family"] != "dipo.rst":
                raise ValueError("discourse context has a foreign primary node")
            children = self.members(row)
            if row["kind"] == "native.rst_singleton" and len(children) == 1:
                return visit(children[0])
            if row["kind"] != "native.rst_node" or len(children) != 2:
                raise ValueError("discourse context requires complete retained binary RST nodes")
            left, right = map(visit, children)
            native = row["native_rst"]
            if [*left, *right] != [
                native["left_start"],
                native["left_end"],
                native["right_start"],
                native["right_end"],
            ]:
                raise ValueError("discourse child ranges differ from retained native RST")
            splits.append(
                dict(
                    left=left,
                    right=right,
                    nuclearity=native["nuclearity"],
                    relation=row["native_label"],
                )
            )
            return left[0], right[1]

        root = visit(self.root)
        if set(located) != set(range(*root)):
            raise ValueError("discourse context requires the complete selected subtree")
        # The bounded native-tree selector uses zero-based local ordinals. Keep
        # the retained offset for receipts rather than changing native metadata.
        offset = root[0]
        local = {ordinal - offset: anchors for ordinal, anchors in located.items()}
        normalized = [
            dict(
                row,
                left=[n - offset for n in row["left"]],
                right=[n - offset for n in row["right"]],
            )
            for row in splits
        ]
        return (
            local,
            prepare_dipo_context(
                dict(root=[0, len(local)], splits=normalized), located_edus=set(local), max_edus=2
            ),
            offset,
        )


def _covers(anchors, focal):
    return bool(focal) and all(
        any(
            a["pin"] == part["pin"]
            and a["pointer"] == part["pointer"]
            and a["start"] <= part["start"] < part["end"] <= a["end"]
            for a in anchors
        )
        for part in focal
    )


def _frame(context, focal):
    children = context.root.get("children", ())
    fields = {edge["role"]: context.terms[edge["target"]] for edge in children if "target" in edge}
    if "predicate" not in fields:
        raise ValueError("frame context lacks its retained predicate member")
    predicate = context.location(fields["predicate"])
    if not predicate:
        return (), ("frame predicate has no exact source location",)
    signals, omissions = [QuerySignal("Predicate", predicate)], []
    metadata = {
        "predicate",
        "focus",
        "voice",
        "polarity",
        "interpretation",
        "layout",
        "clause_role",
    }
    for edge in children:
        if "target" not in edge or edge["role"] in metadata:
            continue
        member = context.terms[edge["target"]]
        role = f"Argument {edge['role']}"
        anchors = context.location(member) if member.get("status") == "interpreted" else ()
        if not anchors:
            omissions.append(f"{role} has no exact source location")
        elif len(signals) < 6:
            signals.append(QuerySignal(role, anchors))
        else:
            omissions.append(f"{role} exceeds the frame signal bound")
    return tuple(signals), tuple(omissions)


def _referent(context, focal):
    located = []
    for member in context.members(context.root):
        if (
            member["kind"] not in {"native.mention", "native.unmapped_mention"}
            or member["family"] != "maverick.mentions"
        ):
            raise ValueError("local referent cluster requires mapped retained native mentions")
        value = member["native_mention"]
        if value["mapping_status"] not in {"mapped", "unmapped"} or value["first"] > value["last"]:
            raise ValueError("local referent cluster has an invalid mention interval")
        located.append(
            (
                value["first"],
                value["last"],
                context.location(member) if value["mapping_status"] == "mapped" else (),
            )
        )
    matching = [(first, last) for first, last, anchors in located if _covers(anchors, focal)]
    if len(matching) != 1:
        raise ValueError("local referent context requires one located focal mention")
    ordered = sorted(
        (row for row in located if row[1] < matching[0][0]), key=lambda row: row[:2], reverse=True
    )
    neighbor = next((anchors for _, _, anchors in ordered if anchors), None)
    if neighbor is None:
        return (), ("no earlier local member has an exact source location",)
    omitted = len(ordered) - 1
    return (QuerySignal("Earlier local mention", neighbor),), (
        (f"{omitted} other earlier members omitted",) if omitted else ()
    )


def _discourse(context, focal):
    located, index, offset = context.discourse
    matches = [edu for edu, anchors in located.items() if _covers(anchors, focal)]
    if len(matches) != 1:
        raise ValueError("discourse context requires one exact focal EDU")
    chosen = index.select(matches[0], max_omitted=8)
    omissions = tuple(
        f"EDUs {[n + offset for n in row['range']]}: {row['reason']}" for row in chosen["omitted"]
    )
    if chosen.get("additional_omitted_ranges"):
        omissions += (f"{chosen['additional_omitted_ranges']} additional EDU ranges omitted",)
    if chosen["sibling"] is None:
        return (), (*omissions, "no eligible adjacent subtree within the EDU bound")
    neighbor, _ = chosen["sibling"]
    return (QuerySignal("Discourse neighbor", located[neighbor]),), omissions


def resolve_query_contexts(
    selection: QueryContextSelection,
    layers: Mapping,
    source_products: Sequence[Mapping[str, Any]],
    source,
) -> dict[str, LocatedQueryContext]:
    """Project primary facts only; callers authenticate live or detached layer closure."""
    products = {row["occurrence_id"]: row for row in source_products}
    resolver = {
        "located-frame-2": _frame,
        "located-referent-2": _referent,
        "located-discourse-neighbor-2": _discourse,
    }[selection.recipe]
    roots, result = {}, {}
    # Reuse one authenticated coordinate map across every selected node. Signal
    # bounds apply to rendering; source conversion must cover the pinned source.
    source_context = NativeSourceContext(
        source,
        (),
        (SourceSlice(source.source_view_id, 0, len(source.text)),),
        "retained primary retrieval signal",
        "primary-query-signal-2",
        "exact retained primary selection",
        max_chars=max(1, len(source.text)),
        max_pieces=max(1, len(source.text)),
    )
    pin = record_source_pin(source)
    for binding in selection.bindings:
        occurrence = products.get(binding.occurrence_id)
        if occurrence is None or any(
            a["precision"] != "exact" or a["pin"] != pin or a["space"] != "native"
            for a in occurrence["anchors"]
        ):
            raise ValueError("query context is outside the located source occurrence population")
        if binding.evidence not in roots:
            if binding.evidence.layer not in layers:
                raise ValueError("query context lacks its exact selected primary layer")
            roots[binding.evidence] = _PrimaryContext(
                layers[binding.evidence.layer],
                binding.evidence,
                selection.recipe,
                source,
                layers,
                source_context,
            )
        context = roots[binding.evidence]
        if not _covers(context.location(context.root), occurrence["anchors"]):
            raise ValueError("query context does not locate the selected occurrence")
        signals, omissions = resolver(context, occurrence["anchors"])
        result[binding.occurrence_id] = LocatedQueryContext(
            selection.recipe, binding.evidence, signals, omissions
        )
    return result
