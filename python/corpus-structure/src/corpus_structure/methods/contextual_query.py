"""One independently attributable context signal for a located retrieval query."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import cached_property
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from corpus_structure.semantic.retained_contributions import RetainedContributionRef

from .contextual_embeddings import identity
from .pm2_dipo_products import prepare_dipo_context
from .pm2_products import EDUView, FrameView, MentionView, TreeView, parser_view

ContextRecipe = Literal["located-frame-1", "located-referent-1", "located-discourse-neighbor-1"]
_PRODUCTS = {
    "located-frame-1": "linguistic.predicate_frame",
    "located-referent-1": "maverick.cluster",
    "located-discourse-neighbor-1": "dipo.tree",
}


class QueryContextBinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    occurrence_id: str = Field(pattern=r"^source-occurrence:[0-9a-f]{64}$")
    evidence: RetainedContributionRef


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
    evidence: RetainedContributionRef
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
            "evidence": self.evidence.model_dump(mode="json"),
            "signals": [
                {"label": signal.label, "anchor_ids": [a["anchor_id"] for a in signal.anchors]}
                for signal in self.signals
            ],
            "omissions": self.omissions,
        }


class _RetainedContext:
    def __init__(self, retained, reference, recipe, pin, nodes):
        rows = retained["contributions"]
        self.rows = {row["contribution_id"]: row for row in rows}
        self.pin = pin
        self.nodes = nodes
        root = self.rows.get(reference.contribution_id)
        if (
            len(self.rows) != len(rows)
            or root is None
            or root["semantic_type"] != _PRODUCTS[recipe]
            or root["pin"] != pin
            or not any(source["pin"] == pin for source in retained["sources"])
        ):
            raise ValueError("query context evidence differs from selected source or recipe")
        self.root = root

    def members(self, row):
        result = []
        for member_id in row.get("members", ()):
            member = self.rows.get(member_id)
            if (
                member is None
                or member["operation_key"] != self.root["operation_key"]
                or member["pin"] != self.pin
            ):
                raise ValueError("query context has a foreign or unavailable member")
            result.append(member)
        return tuple(result)

    def location(self, row):
        if row["semantic_type"] != "source_occurrence":
            raise ValueError("query context requires native occurrence members")
        anchors = tuple(row.get("anchors", ()))
        if not anchors or any(a["precision"] != "exact" for a in anchors):
            return ()
        for anchor in anchors:
            node = self.nodes.get(anchor["pointer"], {})
            start, end = anchor["start"], anchor["end"]
            text = node.get("text", "")
            if (
                anchor["pin"] != self.pin
                or anchor["space"] != "native"
                or type(start) is not int
                or type(end) is not int
                or not 0 <= start < end <= len(text)
                or text[start:end] != anchor["source_piece"]
            ):
                raise ValueError("query context location differs from exact native source")
        return anchors

    def single_location(self, row):
        members = self.members(row)
        if len(members) > 1:
            raise ValueError("query context product has ambiguous locations")
        return self.location(members[0]) if members else ()

    @cached_property
    def discourse(self):
        tree = parser_view(self.root)
        if not isinstance(tree, TreeView):
            raise ValueError("discourse context requires a retained Dipo tree")
        located = {}
        seen = set()
        for member in self.members(self.root):
            if member["semantic_type"] != "dipo.edu":
                raise ValueError("discourse context has a foreign or repeated EDU")
            value = parser_view(member)
            if not isinstance(value, EDUView) or value.arm != tree.arm or value.edu in seen:
                raise ValueError("discourse context has a foreign or repeated EDU")
            seen.add(value.edu)
            anchors = self.single_location(member)
            if anchors:
                located[value.edu] = anchors
        if seen != set(range(tree.root[1])):
            raise ValueError("discourse context has an incomplete leaf population")
        return located, prepare_dipo_context(
            tree.model_dump(mode="json"), located_edus=located.keys(), max_edus=2
        )


def _covers(anchors, focal):
    return bool(focal) and all(
        any(
            a["pointer"] == part["pointer"]
            and a["start"] <= part["start"] < part["end"] <= a["end"]
            for a in anchors
        )
        for part in focal
    )


def _frame(context, focal):
    root = context.root
    value = parser_view(root)
    if not isinstance(value, FrameView):
        raise ValueError("frame context requires a retained HanLP frame")
    locations = {member["item_key"]: context.location(member) for member in context.members(root)}
    if not any(_covers(anchors, focal) for anchors in locations.values()):
        raise ValueError("frame context does not locate the selected occurrence")
    roles = [("Predicate", value.predicate)]
    roles.extend((f"Dependency {arg.role}", arg.location) for arg in value.dependency_arguments)
    for frame in value.srl_frames:
        roles.extend((f"SRL {arg.role}", arg.location) for arg in frame.arguments)
    if not locations.get(value.predicate):
        return (), ("frame predicate has no exact source location",)
    signals, omissions = [], []
    for role, key in dict.fromkeys(roles):
        if not locations.get(key):
            omissions.append(f"{role} has no exact source location")
        elif len(signals) < 6:
            signals.append(QuerySignal(role, locations[key]))
        else:
            omissions.append(f"{role} exceeds the frame signal bound")
    return tuple(signals), tuple(omissions)


def _referent(context, focal):
    located = []
    for member in context.members(context.root):
        if member["semantic_type"] != "maverick.mention":
            raise ValueError("local referent cluster has a non-mention member")
        value = parser_view(member)
        if not isinstance(value, MentionView) or value.first > value.last:
            raise ValueError("local referent cluster has an invalid mention interval")
        located.append((value.first, value.last, context.single_location(member)))
    matching = [(first, last) for first, last, anchors in located if _covers(anchors, focal)]
    if len(matching) != 1:
        raise ValueError("local referent context requires one located focal mention")
    earlier = [(first, last, anchors) for first, last, anchors in located if last < matching[0][0]]
    ordered = sorted(earlier, key=lambda row: row[:2], reverse=True)
    neighbor = next((anchors for _, _, anchors in ordered if anchors), None)
    if neighbor is None:
        return (), ("no earlier local member has an exact source location",)
    omitted = len(ordered) - 1
    return (QuerySignal("Earlier local mention", neighbor),), (
        (f"{omitted} other earlier members omitted",) if omitted else ()
    )


def _discourse(context, focal):
    located, index = context.discourse
    matches = [edu for edu, anchors in located.items() if _covers(anchors, focal)]
    if len(matches) != 1:
        raise ValueError("discourse context requires one exact focal EDU")
    chosen = index.select(matches[0], max_omitted=8)
    omissions = tuple(f"EDUs {row['range']}: {row['reason']}" for row in chosen["omitted"])
    if chosen.get("additional_omitted_ranges"):
        omissions += (f"{chosen['additional_omitted_ranges']} additional EDU ranges omitted",)
    if chosen["sibling"] is None:
        return (), (*omissions, "no eligible adjacent subtree within the EDU bound")
    neighbor, _ = chosen["sibling"]
    return (QuerySignal("Discourse neighbor", located[neighbor]),), omissions


def resolve_query_contexts(
    selection: QueryContextSelection,
    evidence: Sequence[Mapping[str, Any]],
    source_products: Sequence[Mapping[str, Any]],
    nodes: Mapping[str, Any],
    pin: Mapping[str, Any],
) -> dict[str, LocatedQueryContext]:
    """Bind the proposed signals to independently selected native product closure."""
    products = {row["occurrence_id"]: row for row in source_products}
    resolver = {
        "located-frame-1": _frame,
        "located-referent-1": _referent,
        "located-discourse-neighbor-1": _discourse,
    }[selection.recipe]
    roots = {}
    result = {}
    for binding, retained in zip(selection.bindings, evidence, strict=True):
        occurrence = products.get(binding.occurrence_id)
        if occurrence is None or any(a["precision"] != "exact" for a in occurrence["anchors"]):
            raise ValueError("query context is outside the located source occurrence population")
        if binding.evidence not in roots:
            roots[binding.evidence] = _RetainedContext(
                retained, binding.evidence, selection.recipe, pin, nodes
            )
        context = roots[binding.evidence]
        signals, omissions = resolver(context, occurrence["anchors"])
        result[binding.occurrence_id] = LocatedQueryContext(
            selection.recipe, binding.evidence, signals, omissions
        )
    return result
