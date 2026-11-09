"""Project typed parts of the bounded, retained contribution selection.

Native completion owns source and product validation. Here a join never looks
outside the selected task, operation, source pin, and actual membership. Exact
references to inputs from another cut remain references to that cut.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from corpus_structure.methods.pm2_dipo_products import prepare_dipo_context
from corpus_structure.methods.pm2_products import (
    PARSER_PROVIDER,
    PARSER_QUESTIONS,
    ClusterView,
    CueView,
    EDUView,
    FrameView,
    MentionView,
    ParserValue,
    PhraseView,
    TreeView,
    parser_view,
    released_parser_members,
)
from corpus_structure.semantic.contextual_storage import RetainedCandidateListRef
from corpus_structure.semantic.contributions import (
    contribution_payload_contracts,
    validate_contribution_semantics,
)
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.refusals import SemanticRefusal
from corpus_structure.semantic.retained_contributions import RetainedContributionRef
from corpus_structure.semantic.types import PreparedRelease

_CONTEXT_EDUS = 4
_CONTEXT_OMISSIONS = 8

Row = Mapping[str, Any]
Custody = tuple[int, int, str]


def _custody(row: Row) -> Custody:
    return row["selected_task_id"], row["origin_task_id"], row["operation_key"]


def _reference(row: Row) -> dict[str, Any]:
    return {
        key: row[key]
        for key in (
            "selected_task_id",
            "origin_task_id",
            "source_view_id",
            "operation_key",
            "contribution_id",
            "semantic_type",
        )
    }


def _exact_anchors(row: Row) -> tuple[str, ...]:
    return tuple(
        anchor["anchor_id"]
        for anchor in row.get("anchors", ())
        if anchor["space"] == "native" and anchor["precision"] == "exact"
    )


@dataclass(frozen=True)
class _Parts:
    product: Row
    located: Mapping[str, str]
    unavailable: frozenset[str]
    selection: Mapping[tuple[Custody, str], Row]

    @classmethod
    def read(
        cls,
        product: Row,
        keys: Sequence[str],
        missing: Sequence[str],
        selection: Mapping[tuple[Custody, str], Row],
    ) -> _Parts:
        ids = product.get("members", ())
        # The producer keeps the native keys in order and materializes only
        # located members in that same order; never join by text or key alone.
        if (
            len(set(keys)) != len(keys)
            or len(set(missing)) != len(missing)
            or not set(missing).issubset(keys)
            or len(ids) != len(keys) - len(missing)
            or len(set(ids)) != len(ids)
        ):
            raise SemanticRefusal("retained PM2 membership differs from its declared keys")
        unavailable = frozenset(missing)
        return cls(
            product,
            dict(zip((key for key in keys if key not in unavailable), ids, strict=True)),
            unavailable,
            selection,
        )

    def resolve(self, key: str, semantic_type: str) -> tuple[str, Row | None]:
        if key in self.unavailable:
            return "source_unavailable", None
        identity = self.located.get(key)
        if identity is None:
            raise SemanticRefusal("retained PM2 role refers to an undeclared member")
        member = self.selection.get((_custody(self.product), identity))
        if member is None:
            return "outside_selection", None
        if (
            member["item_key"] != key
            or member["semantic_type"] != semantic_type
            or member["pin"] != self.product["pin"]
            or member["source_view_id"] != self.product["source_view_id"]
        ):
            raise SemanticRefusal("retained PM2 role differs from its original source member")
        return "retained", member

    def role(
        self,
        family: str,
        role: str,
        key: str,
        *,
        semantic_type: str = "source_occurrence",
        group: int | None = None,
    ) -> dict[str, Any]:
        state, member = self.resolve(key, semantic_type)
        result: dict[str, Any] = {"role_family": family, "role": role, "member_key": key}
        if group is not None:
            result["group"] = group
        if member is not None:
            result["reference"] = _reference(member)
            if semantic_type == "source_occurrence":
                anchors = _exact_anchors(member)
                if not anchors:
                    raise SemanticRefusal("PM2 source role lacks its exact native anchor")
                result.update(anchor_ids=anchors, occurrence_id=member["occurrence_id"])
                state = "source_located"
        elif key in self.located:
            result["contribution_id"] = self.located[key]
        result["state"] = state
        return result


def _parser_roles(value: ParserValue, parts: _Parts) -> list[dict[str, Any]]:
    if isinstance(value, FrameView):
        if value.focus is None:
            raise SemanticRefusal("retained PM2 frame lacks a focal member")
        roles = [
            parts.role("frame", "predicate", value.predicate),
            parts.role("frame", "focus", value.focus),
            *(
                parts.role("native_dependency", item.role, item.location)
                for item in value.dependency_arguments
            ),
        ]
        for group, frame in enumerate(value.srl_frames):
            if frame.predicate is None:
                raise SemanticRefusal("retained PM2 frame lacks its SRL predicate")
            roles.append(parts.role("native_srl", "PRED", frame.predicate, group=group))
            roles.extend(
                parts.role("native_srl", item.role, item.location, group=group)
                for item in frame.arguments
            )
        return roles
    if isinstance(value, CueView):
        return [
            parts.role("qualifier", "cue", value.location),
            parts.role("qualifier", "marker", value.marker),
            *(
                parts.role(
                    "qualifier_candidate", "host", key, semantic_type="linguistic.predicate_frame"
                )
                for key in value.candidates
            ),
            *(
                [
                    parts.role(
                        "qualifier_candidate",
                        "attribution_source",
                        source,
                        semantic_type="linguistic.predicate_frame",
                    )
                ]
                if (source := value.attribution_source) is not None
                else []
            ),
        ]
    if isinstance(value, ClusterView):
        return [
            parts.role("local_coreference", "mention", key, semantic_type="maverick.mention")
            for key in value.member_keys
        ]
    if isinstance(value, MentionView):
        return [
            parts.role("local_coreference", "mention_extent", key) for key in value.location_keys
        ]
    if isinstance(value, (PhraseView, EDUView)):
        key = value.location_key if isinstance(value, EDUView) else value.location
        if key is None:
            raise SemanticRefusal("retained PM2 product lacks an extent member")
        return [parts.role("source", "extent", key)]
    return []


def interpretation_predecessors(
    value: Row,
) -> tuple[tuple[RetainedContributionRef, ...], RetainedCandidateListRef | None]:
    """Read the exact stored dependency kinds, shared by delivery and detached closure."""
    references = [
        RetainedContributionRef.model_validate(candidate["reference"])
        for candidate in value.get("candidates", ())
        if "reference" in candidate
    ]
    if focus := value.get("focus"):
        references.insert(0, RetainedContributionRef.model_validate(focus))
    retrieval = (
        RetainedCandidateListRef.model_validate(value["retrieval"])
        if value.get("retrieval")
        else None
    )
    if retrieval is not None:
        references.append(retrieval.carrier)
    return tuple(dict.fromkeys(references)), retrieval


def _interpretation_roles(value: Row, parts: _Parts) -> list[dict[str, Any]]:
    roles = [parts.role("answer", "source_witness", key) for key in value.get("location_keys", ())]
    if focus := value.get("focus"):
        roles.append(
            dict(
                role_family="interpretation_input",
                role="focus",
                state="retained_reference",
                reference=RetainedContributionRef.model_validate(focus).model_dump(mode="json"),
            )
        )
    candidates = value.get("candidates", ())
    by_key = {candidate["key"]: candidate for candidate in candidates}
    selected = frozenset(value.get("selected_keys", ()))
    states = value.get("alternative_states", {})
    aliases = value.get("option_aliases", {})
    for native_key in value["native_answer"].get("probabilities", {}):
        key = aliases.get(native_key, native_key)
        option: dict[str, Any] = {
            "role_family": "released_option",
            "role": "option",
            "state": "model_selected" if key in selected else states.get(key, "alternative"),
            "option_key": key,
        }
        if candidate := by_key.get(key):
            option.update(role_family="interpretation_candidate", role="candidate")
            option["semantic_type"] = candidate["semantic_type"]
            if reference := candidate.get("reference"):
                option["reference"] = RetainedContributionRef.model_validate(reference).model_dump(
                    mode="json"
                )
            else:
                option["target_id"] = candidate["target_id"]
                option["representation_digest"] = candidate["representation_digest"]
        roles.append(option)
    return roles


def _assessed_scope(value: Row, row: Row) -> Row:
    """An examined extent locates a question, without becoming answer evidence."""
    scope = value.get("assessed_scope")
    if not isinstance(scope, Mapping) or scope.get("pin") != row["pin"]:
        raise SemanticRefusal("retained interpretation scope differs from its source pin")
    extent, digest = scope.get("projection_extent"), scope.get("scope_digest")
    if (
        not isinstance(extent, list)
        or len(extent) != 2
        or any(type(bound) is not int for bound in extent)
        or not 0 <= extent[0] < extent[1]
        or not isinstance(digest, str)
        or re.fullmatch(r"[0-9a-f]{64}", digest) is None
    ):
        raise SemanticRefusal("retained interpretation lacks an exact assessed extent")
    return scope


def composition_facets(
    operations: Sequence[Row], rows: Sequence[Row], *, prepared: PreparedRelease | None = None
) -> dict[tuple[Custody, str], dict[str, Any]]:
    """Return a private view of named parts under one existing Reader selection."""
    by_operation = {_custody(op): op for op in operations if op.get("cut_member") is True}
    by_ref = {
        (_custody(row), row["contribution_id"]): row
        for row in rows
        if row.get("cut_member") is True
    }
    facets: dict[tuple[Custody, str], dict[str, Any]] = {}
    edus: dict[tuple[Custody, str], EDUView] = {}
    trees: dict[tuple[Custody, str], tuple[Row, TreeView, _Parts]] = {}
    payload_contracts = contribution_payload_contracts(prepared.definitions) if prepared else {}
    for ref, row in by_ref.items():
        semantic_type = row["semantic_type"]
        parser = PARSER_PROVIDER.get(semantic_type)
        interpretation = semantic_type.startswith("interpretation.")
        if parser is None and not interpretation:
            continue
        operation = by_operation.get(ref[0])
        if (
            operation is None
            or operation["source_view_id"] != row["source_view_id"]
            or operation["source"] != row["pin"]["source"]
            or (parser is not None and operation["question"] != PARSER_QUESTIONS[parser])
            or (
                interpretation
                and operation["question"] != semantic_type.removeprefix("interpretation.")
            )
        ):
            raise SemanticRefusal("PM2 contribution lacks its exact producing operation")
        try:
            parser_value = parser_view(row) if parser is not None else None
            if prepared is not None and semantic_type in payload_contracts:
                validate_contribution_semantics(
                    prepared,
                    row,
                    question=operation["question"],
                    payload_contracts=payload_contracts,
                )
                if parser_value is not None:
                    released_parser_members(parser_value)
        except (KeyError, ValueError) as error:
            raise SemanticRefusal("retained PM2 payload differs from its released roles") from error
        value = source_python(row["value"]) if interpretation else {}
        parts = _Parts.read(
            row,
            parser_value.location_keys if parser_value else value.get("location_keys", ()),
            parser_value.unlocated_members if parser_value else value.get("unlocated_members", ()),
            by_ref,
        )
        facets[ref] = {
            "version": "private-contribution-composition-1",
            "standing": "retained_private",
            "operation_question": operation["question"],
            "operation_version": operation["operation_version"],
            "operation_outcome": operation["outcome"],
            "roles": (
                _parser_roles(parser_value, parts)
                if parser_value is not None
                else _interpretation_roles(value, parts)
            ),
        }
        if interpretation:
            facets[ref]["interpretation_state"] = value["state"]
            facets[ref]["assessed_scope"] = _assessed_scope(value, row)
            if value.get("normalization") == "source_exact":
                facets[ref]["normalization"] = {
                    "state": "source_exact",
                    "decimal": value["normalized_value"],
                }
            if value.get("answer_kind") == "noul":
                facets[ref]["binary_observation"] = value["binary_observation"]
            if value.get("retrieval") is not None:
                facets[ref]["candidate_inventory"] = RetainedCandidateListRef.model_validate(
                    value["retrieval"]
                ).model_dump(mode="json")
        elif isinstance(parser_value, EDUView):
            edus[ref] = parser_value
            state = facets[ref]["roles"][0]["state"]
            facets[ref]["discourse_context"] = {
                "outcome": "unavailable",
                "reason": {
                    "source_located": "tree_outside_selection",
                    "source_unavailable": "focal_edu_unmapped",
                    "outside_selection": "focal_anchor_outside_selection",
                }[state],
            }
        elif isinstance(parser_value, TreeView):
            trees[ref] = (row, parser_value, parts)

    for ref, (tree, value, parts) in trees.items():
        located = {}
        if len(value.location_keys) != value.root[1]:
            raise SemanticRefusal("Dipo tree and retained EDU population differ")
        for index, key in enumerate(value.location_keys):
            _, edu = parts.resolve(key, "dipo.edu")
            if edu is None:
                continue
            edu_ref = ref[0], edu["contribution_id"]
            meaning = edus[edu_ref]
            if meaning.arm != value.arm or meaning.edu != index:
                raise SemanticRefusal("Dipo context member differs from its native arm or order")
            if any(role["state"] == "source_located" for role in facets[edu_ref]["roles"]):
                located[index] = edu
        topology = prepare_dipo_context(
            value.model_dump(mode="json"), located_edus=located.keys(), max_edus=_CONTEXT_EDUS
        )
        for focal, edu in located.items():
            context = topology.select(focal, max_omitted=_CONTEXT_OMISSIONS)
            sibling = context["sibling"]
            facets[(ref[0], edu["contribution_id"])]["discourse_context"] = {
                **context,
                "tree": _reference(tree),
                "neighbors": [_reference(located[i]) for i in range(*sibling)] if sibling else [],
            }
    return facets
