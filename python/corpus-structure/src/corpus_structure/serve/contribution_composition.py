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
from corpus_structure.methods.pm2_gliner_classification import (
    FAMILY as CLASSIFICATION_FAMILY,
)
from corpus_structure.methods.pm2_gliner_classification import (
    METHOD as CLASSIFICATION_METHOD,
)
from corpus_structure.methods.pm2_gliner_classification import (
    VERSION as CLASSIFICATION_VERSION,
)
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
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.refusals import SemanticRefusal
from corpus_structure.semantic.retained_contributions import RetainedContributionRef
from corpus_structure.semantic.types import PreparedRelease

_CONTEXT_EDUS = 4
_CONTEXT_OMISSIONS = 8
_CLAUSE_LABELS = frozenset({"S", "SBAR", "SBARQ", "SINV", "SQ"})
_MODIFIER_ROLES = frozenset({"TMP", "PNC", "PRP", "MNR", "CAU"})

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


def _frame_associations(frame: FrameView, parts: _Parts) -> list[dict[str, Any]]:
    """Expose explicit SRL modifiers without turning native roles into semantic claims."""
    host = parts.role("frame", "predicate", frame.predicate)
    if host["state"] != "source_located":
        return []
    result = []
    for group, reading in enumerate(frame.srl_frames):
        for argument in reading.arguments:
            # PropBank continuation and reference roles keep their native spelling.
            role = argument.role.removeprefix("C-").removeprefix("R-")
            scheme, _, modifier_role = role.partition("-")
            if scheme not in {"ARGM", "AM"} or modifier_role not in _MODIFIER_ROLES:
                continue
            modifier = parts.role("native_srl", argument.role, argument.location, group=group)
            if modifier["state"] == "source_located":
                result.append(
                    dict(basis="native_srl_group", status="candidate", host=host, modifier=modifier)
                )
    return result


def _cue_associations(cue: CueView, parts: _Parts) -> list[dict[str, Any]]:
    qualifier = parts.role("qualifier", "cue", cue.location)
    marker = parts.role("qualifier", "marker", cue.marker)
    if qualifier["state"] != "source_located" or marker["state"] != "source_located":
        return []
    result = []
    for key in cue.candidates:
        _, frame = parts.resolve(key, "linguistic.predicate_frame")
        if frame is None:
            continue
        value = parser_view(frame)
        if not isinstance(value, FrameView):
            raise SemanticRefusal("retained qualifier candidate is not a predicate frame")
        frame_parts = _Parts.read(
            frame, value.location_keys, value.unlocated_members, parts.selection
        )
        host = frame_parts.role("qualifier_candidate", "host_predicate", value.predicate)
        if host["state"] == "source_located":
            result.append(
                dict(
                    basis="native_qualifier_cue",
                    status="candidate",
                    qualifier_kind=cue.kind,
                    qualifier=qualifier,
                    marker=marker,
                    host_frame=_reference(frame),
                    host=host,
                )
            )
    return result


def _located_member(parts: _Parts, key: str) -> Row | None:
    _, member = parts.resolve(key, "source_occurrence")
    if (
        member is not None
        and member["anchors"]
        and len(_exact_anchors(member)) == len(member["anchors"])
    ):
        return member
    return None


def _contains_source(container: Row, contained: Row) -> bool:
    """Check authenticated native source extents, never equality of display strings."""
    if container["pin"] != contained["pin"]:
        return False
    outer = [a for a in container["anchors"] if "pointer" in a and "start" in a and "end" in a]
    inner = [a for a in contained["anchors"] if "pointer" in a and "start" in a and "end" in a]
    return (
        bool(inner)
        and len(inner) == len(contained["anchors"])
        and all(
            any(
                a["space"] == b["space"] == "native"
                and a["precision"] == b["precision"] == "exact"
                and a["pointer"] == b["pointer"]
                and a["start"] <= b["start"] < b["end"] <= a["end"]
                for a in outer
            )
            for b in inner
        )
    )


def _local_referents(
    clusters: Sequence[tuple[Row, ClusterView, _Parts]],
    nominal_phrases: Mapping[tuple[int, tuple[str, ...]], Row],
    facets: Mapping[tuple[Custody, str], dict[str, Any]],
) -> None:
    for cluster, value, parts in clusters:
        located: list[tuple[MentionView, Row, Row]] = []
        for key in value.member_keys:
            _, member = parts.resolve(key, "maverick.mention")
            if member is None:
                continue
            mention = parser_view(member)
            if not isinstance(mention, MentionView) or len(mention.location_keys) != 1:
                raise SemanticRefusal("retained local referent lacks one exact mention extent")
            mention_parts = _Parts.read(
                member, mention.location_keys, mention.unlocated_members, parts.selection
            )
            location = _located_member(mention_parts, mention.location_keys[0])
            if location is not None:
                located.append((mention, member, location))
        located.sort(key=lambda entry: (entry[0].first, entry[0].last))
        for mention, focal, location in located:
            earlier = [row for row in located if row[0].last < mention.first]
            if not earlier:
                continue
            _, nearest, nearest_extent = earlier[-1]
            nominal = None
            for _, candidate, extent in reversed(earlier):
                phrase = nominal_phrases.get((extent["source_view_id"], _exact_anchors(extent)))
                if phrase is not None and phrase["pin"] == extent["pin"]:
                    nominal = {
                        "mention": _reference(candidate),
                        "anchor_ids": _exact_anchors(extent),
                        "phrase": _reference(phrase),
                    }
                    break
            facet = facets[(_custody(focal), focal["contribution_id"])]
            if "local_referent_candidates" in facet:
                raise SemanticRefusal("one local mention has competing retained clusters")
            facet["local_referent_candidates"] = {
                "basis": "native_local_cluster",
                "status": "candidate",
                "cluster": _reference(cluster),
                "focal_anchor_ids": _exact_anchors(location),
                "nearest": {
                    "mention": _reference(nearest),
                    "anchor_ids": _exact_anchors(nearest_extent),
                },
                "nominal": nominal,
            }


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
    native = value["native_answer"]
    native_keys = (
        native["offered_keys"]
        if native.get("type") == "gliner_classification"
        else native.get("probabilities", {})
    )
    for native_key in native_keys:
        key = aliases.get(native_key, native_key)
        option: dict[str, Any] = {
            "role_family": "released_option",
            "role": "option",
            "state": "model_selected" if key in selected else states.get(key, "alternative"),
            "option_key": key,
        }
        if native.get("type") == "gliner_classification" and key in native["scores"]:
            option["native_score"] = native["scores"][key]
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


_PREDICATE_FRAMES = "source_predicate_frames"
_PREDICATE_INTERPRETATION = "source_predicate_interpretation"
_PREDICATE_ROLE_VERSIONS = {"3", "4", "5", "6"}
_PREDICATE_PRODUCTS = {
    "structural.predicate_frame": ("predicate_frame", _PREDICATE_FRAMES),
    "structural.predicate_cue": ("predicate_cue", _PREDICATE_FRAMES),
    "structural.predicate_reading": ("predicate_reading", _PREDICATE_INTERPRETATION),
    "structural.predicate_qualification": ("predicate_qualifier", _PREDICATE_INTERPRETATION),
}


def _predicate_scope(row: Row) -> tuple[Any, ...]:
    component = row["component"]
    return (
        row["selected_task_id"],
        row["origin_task_id"],
        component["question_version"],
        component["scope"],
        component.get("effective_version"),
    )


class _PredicateParts:
    """Project retained roles across the two operations in one exact task."""

    def __init__(
        self,
        rows: Mapping[tuple[Custody, str], Row],
        operations: Mapping[Custody, Row],
    ):
        self.operations = operations
        self.rows = {
            (task, origin, identity): row for ((task, origin, _), identity), row in rows.items()
        }
        self.hosts: dict[tuple[Any, ...], list[str]] = {}
        for (_, identity), row in rows.items():
            if row["semantic_type"] != "structural.predicate_frame":
                continue
            component = row.get("component") or {}
            if component.get("question_version") not in _PREDICATE_ROLE_VERSIONS:
                continue
            key = (
                *_predicate_scope(row),
                component["annotation"],
                component["block"],
                component["predicate_token"],
            )
            self.hosts.setdefault(key, []).append(identity)

    def _part(self, row: Row, identity: str) -> Row | None:
        return self.rows.get((row["selected_task_id"], row["origin_task_id"], identity))

    def _role(self, row: Row, role: str, identity: str, semantic_type: str) -> dict[str, Any]:
        part = self._part(row, identity)
        result: dict[str, Any] = {
            "role_family": "predicate_composition",
            "role": role,
            "contribution_id": identity,
            "state": "outside_selection",
        }
        if part is None:
            return result
        operation = self.operations.get(_custody(part))
        expected = _PREDICATE_PRODUCTS.get(semantic_type)
        question = expected[1] if expected is not None else _PREDICATE_FRAMES
        if (
            part["pin"] != row["pin"]
            or part["source_view_id"] != row["source_view_id"]
            or part["semantic_type"] != semantic_type
            or operation is None
            or operation["question"] != question
            or operation["operation_version"] != row["component"]["question_version"]
            or (expected is not None and _predicate_scope(part) != _predicate_scope(row))
            or (
                semantic_type == "structural.predicate_member"
                and source_python(part["value"])["role"] != role
            )
        ):
            raise SemanticRefusal("retained predicate role differs from its source member")
        result.update(state="retained", reference=_reference(part))
        if semantic_type in {"structural.predicate_member", "structural.predicate_cue"}:
            anchors = _exact_anchors(part)
            if not anchors or len(anchors) != len(part["anchors"]):
                raise SemanticRefusal("retained predicate role lacks its exact native anchors")
            result.update(
                state="source_located", anchor_ids=anchors, occurrence_id=part["occurrence_id"]
            )
        return result

    def facet(self, row: Row, operation: Row, prepared: PreparedRelease | None) -> dict[str, Any]:
        kind, question = _PREDICATE_PRODUCTS[row["semantic_type"]]
        component = row["component"]
        if (
            component["kind"] != kind
            or component["question"] != question
            or component["question_version"] != operation["operation_version"]
            or operation["question"] != question
            or operation["source_view_id"] != row["source_view_id"]
            or operation["source"] != row["pin"]["source"]
        ):
            raise SemanticRefusal("predicate composition lacks its exact producing operation")
        facet: dict[str, Any] = {
            "version": "private-contribution-composition-1",
            "standing": "retained_private",
            "operation_question": question,
            "operation_version": operation["operation_version"],
            "operation_outcome": operation["outcome"],
            "scope": component["scope"],
            "effective_version": component.get("effective_version"),
            "roles": [],
        }
        roles = facet["roles"]
        if kind == "predicate_frame":
            for member in component["frame_members"]:
                if member["contribution"] not in row["members"]:
                    raise SemanticRefusal("retained predicate frame refers outside its members")
                located = self._role(
                    row, member["role"], member["contribution"], "structural.predicate_member"
                )
                located["role_outcome"] = member["outcome"]
                roles.append(located)
            roles.extend(
                {
                    "role_family": "predicate_composition",
                    "role": member["role"],
                    "state": member["reason"],
                    "token_indices": member["token_indices"],
                }
                for member in component.get("unlocated_roles") or ()
            )
            facet["focus_state"] = component["focus_state"]
        elif kind == "predicate_cue":
            roles.append(
                self._role(row, "qualifier", row["contribution_id"], "structural.predicate_cue")
            )
            if marker := component.get("marker_member"):
                if marker not in row["members"]:
                    raise SemanticRefusal("retained predicate cue refers outside its members")
                roles.append(self._role(row, "marker", marker, "structural.predicate_member"))
            facet.update(qualifier_kind=component["cue_kind"], host_state=component["host_state"])
            if host_ids := component.get("cross_block_hosts"):
                roles.extend(
                    self._role(row, "candidate_host", host, "structural.predicate_frame")
                    for host in host_ids
                )
            else:
                for token in component.get("candidate_tokens") or ():
                    hosts = self.hosts.get(
                        (*_predicate_scope(row), component["annotation"], component["block"], token)
                    )
                    if not hosts:
                        roles.append(
                            {
                                "role_family": "predicate_composition",
                                "role": "candidate_host",
                                "state": "retained_candidate_token",
                                "token_index": token,
                            }
                        )
                        continue
                    roles.extend(
                        self._role(row, "candidate_host", host, "structural.predicate_frame")
                        | {"token_index": token}
                        for host in hosts
                    )
        elif kind == "predicate_reading":
            frame = component["frame"]
            if tuple(row["members"]) != (frame,):
                raise SemanticRefusal("retained predicate reading differs from its frame")
            roles.append(self._role(row, "host", frame, "structural.predicate_frame"))
            facet.update(reading=component["reading"], polarity=component["polarity"])
        else:
            if prepared is not None:
                try:
                    prepared.validate_json(
                        "PredicateQualifierComponent", canonical_bytes(component)
                    )
                except (KeyError, ValueError) as error:
                    raise SemanticRefusal("retained attachment differs from its release") from error
            qualifier, host = (
                component["qualifier_contribution_id"],
                component["host_contribution_id"],
            )
            endpoints = (("qualifier", qualifier), ("host", host))
            reading = component.get("interpretation_member")
            members = (qualifier, host, reading) if reading else (qualifier, host)
            if (
                row["kind"] != "relation"
                or tuple((part["role"], part["contribution_id"]) for part in row["endpoints"])
                != endpoints
                or tuple(row["members"]) != members
                or not set(members).issubset(row["computation_dependencies"])
            ):
                raise SemanticRefusal(
                    "retained predicate attachment differs from its directed endpoints"
                )
            roles.extend(
                (
                    self._role(row, "qualifier", qualifier, "structural.predicate_cue"),
                    self._role(row, "host", host, "structural.predicate_frame"),
                )
            )
            cue = self._part(row, qualifier)
            if cue is not None and (
                cue["component"]["cue_kind"] != component["qualifier_kind"]
                or cue["component"]["host_state"] != "located"
            ):
                raise SemanticRefusal("retained predicate attachment differs from its qualifier")
            if reading:
                roles.append(
                    self._role(row, "host_reading", reading, "structural.predicate_reading")
                )
                host_reading = self._part(row, reading)
                if host_reading is not None and host_reading["component"]["frame"] != host:
                    raise SemanticRefusal(
                        "retained predicate attachment uses a foreign host reading"
                    )
            facet["qualifier_kind"] = component["qualifier_kind"]
            if condition := component.get("condition"):
                facet["condition"] = source_python(condition)
        return facet


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
    frames: list[tuple[tuple[Custody, str], FrameView, _Parts]] = []
    clauses: dict[tuple[Custody, int], list[tuple[Row, Row]]] = {}
    nominals: dict[tuple[int, tuple[str, ...]], Row] = {}
    clusters: list[tuple[Row, ClusterView, _Parts]] = []
    payload_contracts = contribution_payload_contracts(prepared.definitions) if prepared else {}
    predicate_parts = None
    for ref, row in by_ref.items():
        semantic_type = row["semantic_type"]
        if (
            semantic_type in _PREDICATE_PRODUCTS
            and (row.get("component") or {}).get("question_version") in _PREDICATE_ROLE_VERSIONS
        ):
            operation = by_operation.get(ref[0])
            if operation is None:
                raise SemanticRefusal("predicate composition lacks its exact producing operation")
            if predicate_parts is None:
                predicate_parts = _PredicateParts(by_ref, by_operation)
            facets[ref] = predicate_parts.facet(row, operation, prepared)
            continue
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
        if interpretation:
            is_classification = row.get("method") == CLASSIFICATION_METHOD
            if (
                value["native_answer"].get("type") == "gliner_classification"
            ) != is_classification or (
                is_classification
                and (
                    operation["operation_version"] != CLASSIFICATION_VERSION
                    or operation["question"] != CLASSIFICATION_FAMILY
                )
            ):
                raise SemanticRefusal("classification differs from its exact producing method")
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
        elif isinstance(parser_value, FrameView):
            associations = _frame_associations(parser_value, parts)
            if associations:
                facets[ref]["modifier_candidates"] = associations
            if parser_value.sentence is not None:
                frames.append((ref, parser_value, parts))
        elif isinstance(parser_value, CueView):
            associations = _cue_associations(parser_value, parts)
            if associations:
                facets[ref]["qualifier_host_candidates"] = associations
        elif isinstance(parser_value, PhraseView):
            location = _located_member(parts, parser_value.location)
            if location is not None and parser_value.sentence is not None:
                if parser_value.label in _CLAUSE_LABELS:
                    clauses.setdefault((ref[0], parser_value.sentence), []).append((row, location))
                elif (
                    parser_value.label == "NP"
                    and sum(
                        len(anchor.get("source_piece", "").split())
                        for anchor in location["anchors"]
                    )
                    > 1
                ):
                    # A singleton PTB NP can be a bare pronoun. This bounded
                    # comparator claims only longer, exactly supported phrases.
                    key = (location["source_view_id"], _exact_anchors(location))
                    # Several retained runs can have the same phrase; preserve the exact
                    # selected reference and make the choice independent of row order.
                    previous = nominals.get(key)
                    if previous is None or (_custody(row), row["contribution_id"]) < (
                        _custody(previous),
                        previous["contribution_id"],
                    ):
                        nominals[key] = row
        elif isinstance(parser_value, ClusterView):
            clusters.append((row, parser_value, parts))

    for ref, frame, parts in frames:
        host = _located_member(parts, frame.predicate)
        if host is None or frame.sentence is None:
            continue
        containing = [
            {"clause": _reference(clause), "anchor_ids": _exact_anchors(location)}
            for clause, location in clauses.get((ref[0], frame.sentence), ())
            if _contains_source(location, host)
        ]
        if containing:
            facets[ref]["clause_containment"] = containing
    _local_referents(clusters, nominals, facets)
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
