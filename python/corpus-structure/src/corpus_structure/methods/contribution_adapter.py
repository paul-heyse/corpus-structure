"""Versioned recovery of actual returned products; no model loading or admission.

The score diagnostics and whole-record assembler are consumers of reports, not their
inventory. This adapter visits returned objects before either can discard a local part.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.source_contexts import (
    ContextRefused,
    NativeSourceContext,
    evidence_anchor,
    native_item_anchor,
    record_source_pin,
)

from .gliner import GlinerPack, GlinerPreparation, GlinerRefused, GlinerReport

ADAPTER_VERSION = "retained-native-contributions-1"
LOCAL_ADAPTER_VERSION = "native-local-contributions-2"


def _digest(value: Any) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


@dataclass(frozen=True)
class ContributionBatch:
    operations: tuple[Mapping[str, Any], ...] = ()
    contributions: tuple[Mapping[str, Any], ...] = ()
    coordinate_texts: tuple[Mapping[str, Any], ...] = ()

    @classmethod
    def combine(cls, batches: Sequence[ContributionBatch]) -> ContributionBatch:
        return cls(
            tuple(row for batch in batches for row in batch.operations),
            tuple(row for batch in batches for row in batch.contributions),
            tuple(row for batch in batches for row in batch.coordinate_texts),
        )


def restore_report(
    retained: Mapping[str, Any], context: NativeSourceContext, profiles: Mapping[str, str]
) -> GlinerReport:
    """Recover only exactly reconstructible report preparation, preserving raw bytes."""
    row = dict(retained)
    if row.get("context_digest") != context.dependency_digest:
        raise GlinerRefused("retained context digest cannot be reconstructed")
    preparation = dict(row["preparation"])
    consumed = context.text + preparation.get("synthetic_suffix", "")
    retained_text = preparation.pop("consumed_text", None)
    expected = preparation.pop("consumed_text_sha256", None)
    if expected is not None:
        if sha256(consumed.encode()).hexdigest() != expected:
            raise GlinerRefused("retained preparation text digest differs")
    elif retained_text != consumed:
        raise GlinerRefused("retained preparation text is unavailable or differs")
    profile_ref = row.pop("effective_profile_ref", None)
    if profile_ref is not None:
        effective = profiles.get(profile_ref)
        if effective is None or sha256(effective.encode()).hexdigest() != profile_ref:
            raise GlinerRefused("retained effective profile is unavailable or differs")
        row["effective_profile_json"] = effective
    if not isinstance(row.get("effective_profile_json"), str):
        raise GlinerRefused("retained effective profile is unavailable")
    row["preparation"] = GlinerPreparation(consumed_text=consumed, **preparation)
    if "diagnostics" in row:
        row["diagnostics"] = tuple(tuple(pair) for pair in row["diagnostics"])
    return GlinerReport(**row)


def _score(value):
    if not isinstance(value, Mapping) or "confidence" not in value:
        return dict(score_state="missing")
    score = value["confidence"]
    supported = type(score) in {int, float} and math.isfinite(score) and 0 <= score <= 1
    return (
        dict(score_state="native", score=source_value(score))
        if supported
        else dict(score_state="unsupported")
    )


def _map_returned_span(context, raw):
    if not isinstance(raw, Mapping):
        raise GlinerRefused("returned literal lacks source coordinates")
    start, end, text = raw.get("start"), raw.get("end"), raw.get("text")
    if type(start) is not int or type(end) is not int or not isinstance(text, str):
        raise GlinerRefused("returned literal lacks typed source coordinates")
    return context.map_span(start, end, literal=text, allow_multiple=True)


class _Builder:
    def __init__(
        self,
        context,
        *,
        report_digest,
        computation,
        producer,
        item_key,
        dependencies,
        question="recover_returned_local_contributions",
        operation_version=ADAPTER_VERSION,
    ):
        from corpus_structure.semantic.contributions import operation_identity

        self.context = context
        self.pin = record_source_pin(context.primary)
        self.operation = dict(
            question=question,
            operation_version=operation_version,
            outcome="succeeded",
            inspected_count=0,
            emitted_count=0,
            report_digest=report_digest,
            inputs=(),
            computation_dependencies=tuple(
                sorted(
                    {
                        "adapter:" + ADAPTER_VERSION,
                        "producer:" + producer,
                        "context:" + context.dependency_digest,
                        "computation:" + computation,
                        *dependencies,
                    }
                )
            ),
        )
        # An invocation can contain the same report more than once. Its retained position
        # remains observation identity while physical occurrence is source-owned.
        self.operation["operation_key"] = operation_identity(
            {**self.operation, "item_key": item_key}
        )
        self.rows = []
        self.coordinates = {}
        self.unsupported = False

    def add(self, *, kind, semantic_type, item_key, anchors=(), **values):
        from corpus_structure.semantic.contributions import (
            contribution_identity,
            occurrence_identity,
        )

        row = dict(
            contract="RetainedContributionSemantics",
            kind=kind,
            semantic_type=semantic_type,
            operation_key=self.operation["operation_key"],
            item_key=item_key,
            pin=self.pin,
            anchors=tuple(anchors),
            endpoints=(),
            members=(),
            disposition="candidate",
            standing="retained_private",
            score_state="missing",
            computation_dependencies=self.operation["computation_dependencies"],
        )
        row.update(values)
        if anchors:
            row["occurrence_id"] = occurrence_identity(anchors)
        row["contribution_id"] = contribution_identity(row)
        self.rows.append(row)
        return row["contribution_id"]

    def field(self, *, semantic_type, item_key, raw, locate, literal=True):
        self.operation["inspected_count"] += 1
        anchors, reason, unlocated = [], None, False
        if raw is None:
            literal = False
            reason = "returned null field; no located value or source absence is established"
        if literal:
            try:
                for piece in locate():
                    anchor, coordinate = evidence_anchor(self.context, piece, native=True)
                    anchors.append(anchor)
                    self.coordinates[
                        canonical_bytes({k: v for k, v in coordinate.items() if k != "text"})
                    ] = coordinate
                if not anchors:
                    raise ContextRefused("returned literal has no source pieces")
            except (ContextRefused, GlinerRefused, KeyError, TypeError, ValueError) as error:
                anchors = []
                reason = str(error)
                unlocated = True
        occurrence = None
        if anchors:
            occurrence = self.add(
                kind="occurrence",
                semantic_type="source_occurrence",
                item_key=item_key + "/occurrence",
                anchors=anchors,
            )
        values: dict[str, Any] = dict(value=source_value(raw), **_score(raw))
        if occurrence:
            values["endpoints"] = (dict(role="occurrence", contribution_id=occurrence),)
        if reason:
            values["reason"] = reason
        proposal = self.add(
            kind="proposal",
            semantic_type=semantic_type,
            item_key=item_key,
            anchors=anchors,
            **values,
        )
        if unlocated:
            self.add(
                kind="diagnostic",
                semantic_type="unlocated_returned_proposal",
                item_key=item_key + "/diagnostic",
                reason=reason,
                endpoints=(dict(role="proposal", contribution_id=proposal),),
                disposition="unresolved",
            )
        return proposal

    def diagnostic(self, item_key, raw, reason):
        self.unsupported = True
        return self.add(
            kind="diagnostic",
            semantic_type="unsupported_returned_shape",
            item_key=item_key,
            value=source_value(raw),
            reason=reason,
            disposition="unresolved",
        )

    def finish(self):
        self.operation["emitted_count"] = len(self.rows)
        if self.unsupported:
            self.operation["outcome"] = "limited"
            self.operation["reason"] = "unsupported returned shapes retained as diagnostics"
        elif not self.rows:
            self.operation["outcome"] = "empty"
        return ContributionBatch(
            (self.operation,), tuple(self.rows), tuple(self.coordinates.values())
        )


def adapt_report(
    report: GlinerReport,
    context: NativeSourceContext,
    *,
    pack: GlinerPack,
    item_key: str,
    dependencies: Sequence[str] = (),
) -> ContributionBatch:
    """Visit all returned groups and fields regardless of score or record viability."""
    if report.pack != pack.fingerprint:
        raise GlinerRefused("retained report pack is unavailable or differs")
    if report.context_digest != context.dependency_digest:
        raise GlinerRefused("report belongs to another source context")
    if report.preparation.consumed_text != context.text + report.preparation.synthetic_suffix:
        raise GlinerRefused("provider preprocessing changed the source prefix")
    if pack.version == "native-local-v1":
        return _adapt_local_report(
            report, context, pack=pack, item_key=item_key, dependencies=dependencies
        )
    builder = _Builder(
        context,
        report_digest=sha256(report.raw_json.encode()).hexdigest(),
        computation=report.computation,
        producer="gliner_returned",
        item_key=item_key,
        dependencies=(
            "pack:" + report.pack,
            "profile:" + report.profile,
            "effective-profile:" + sha256(report.effective_profile_json.encode()).hexdigest(),
            "preparation:" + _digest(asdict(report.preparation)),
            *dependencies,
        ),
    )
    declaration = json.loads(pack.declaration_json).get("structures", {})
    raw = report.raw
    if not isinstance(raw, dict):
        builder.diagnostic("$", raw, "returned report is not an object")
        return builder.finish()
    for family, groups in raw.items():
        path = "$[" + json.dumps(family) + "]"
        if family not in declaration or not isinstance(groups, list):
            builder.diagnostic(path, groups, "returned family is undeclared or not a group list")
            continue
        fields = {field["name"]: field for field in declaration[family].get("fields", ())}
        for group_index, group in enumerate(groups):
            group_path = f"{path}[{group_index}]"
            if not isinstance(group, dict):
                builder.diagnostic(group_path, group, "returned group is not an object")
                continue
            members = []
            for name, value in group.items():
                field_path = group_path + "[" + json.dumps(name) + "]"
                if name == "confidence":
                    # A group score is not a role or a hidden extra proposal.
                    members.append(
                        builder.add(
                            kind="diagnostic",
                            semantic_type="native_group_score",
                            item_key=field_path,
                            value=source_value(value),
                            **_score({"confidence": value}),
                        )
                    )
                    continue
                if name not in fields:
                    members.append(
                        builder.diagnostic(field_path, value, "undeclared returned field")
                    )
                    continue
                fragments = value if isinstance(value, list) else [value]
                for fragment_index, fragment in enumerate(fragments):
                    fragment_path = (
                        f"{field_path}[{fragment_index}]" if isinstance(value, list) else field_path
                    )
                    classified = bool(fields[name].get("choices"))
                    members.append(
                        builder.field(
                            semantic_type=family + "." + name,
                            item_key=fragment_path,
                            raw=fragment,
                            literal=not classified,
                            locate=lambda fragment=fragment: _map_returned_span(context, fragment),
                        )
                    )
                if isinstance(value, list) and not value:
                    members.append(
                        builder.add(
                            kind="proposal",
                            semantic_type=family + "." + name,
                            item_key=field_path,
                            value=source_value(value),
                            reason="returned empty field list; no source absence is established",
                        )
                    )
            if not members:
                members.append(
                    builder.add(
                        kind="diagnostic",
                        semantic_type="empty_returned_group",
                        item_key=group_path + "/empty",
                        value=source_value(group),
                        reason="returned group has no fields",
                    )
                )
            builder.add(
                kind="composite",
                semantic_type=family + ".returned_group",
                item_key=group_path,
                members=tuple(members),
                reason="producer grouping proposal; no whole-record completeness is asserted",
            )
    return _with_returned_attachments(builder.finish(), context, pack=pack, item_key=item_key)


def _adapt_local_report(report, context, *, pack, item_key, dependencies):
    """Retain entity-conditioned attributes and independently located relation ends.

    This is a new operation version. Historical grouped-record adapters retain
    their original identity and meaning. Missing attributes are not negative labels.
    """
    declaration = pack.compile().to_dict()
    builder = _Builder(
        context,
        report_digest=sha256(report.raw_json.encode()).hexdigest(),
        computation=report.computation,
        producer="gliner_local_returned",
        item_key=item_key,
        dependencies=(
            "pack:" + report.pack,
            "profile:" + report.profile,
            "effective-profile:" + sha256(report.effective_profile_json.encode()).hexdigest(),
            *dependencies,
        ),
        question="retain_native_spans_attributes_relations",
        operation_version=LOCAL_ADAPTER_VERSION,
    )
    raw = report.raw
    if not isinstance(raw, dict):
        builder.diagnostic("$", raw, "returned local report is not an object")
        return builder.finish()
    for key in raw.keys() - {"entities", "relation_extraction"}:
        builder.diagnostic(key, raw[key], "undeclared local output channel")
    entities = raw.get("entities", {})
    if not isinstance(entities, dict):
        builder.diagnostic("entities", entities, "entity channel is not an object")
        entities = {}
    attributes = declaration.get("entity_attributes", {})
    located = {}
    for entity_type, values in entities.items():
        if entity_type not in declaration.get("entities", ()) or not isinstance(values, list):
            builder.diagnostic(entity_type, values, "undeclared entity type or invalid population")
            continue
        for ordinal, value in enumerate(values):
            path = f"entities/{entity_type}/{ordinal}"
            identity = builder.field(
                semantic_type="entity." + entity_type,
                item_key=path,
                raw=value,
                locate=lambda value=value: _map_returned_span(context, value),
            )
            proposal = next(
                row for row in reversed(builder.rows) if row["contribution_id"] == identity
            )
            if proposal["anchors"]:
                key = (value["start"], value["end"], value["text"])
                located.setdefault(key, []).append(identity)
            if not isinstance(value, Mapping):
                continue
            for name, attribute in value.items():
                if name in {"text", "start", "end", "confidence"}:
                    continue
                config = attributes.get(name)
                if config is None or entity_type not in config.get(
                    "applies_to", declaration.get("entities", ())
                ):
                    builder.diagnostic(
                        path + "/" + name, attribute, "undeclared or inapplicable span attribute"
                    )
                    continue
                if isinstance(attribute, list) and not config.get("multi_label", False):
                    builder.diagnostic(
                        path + "/" + name,
                        attribute,
                        "single-label attribute returned several labels",
                    )
                    continue
                returned = attribute if isinstance(attribute, list) else [attribute]
                for index, label in enumerate(returned):
                    content = label.get("label") if isinstance(label, Mapping) else label
                    if content not in config["labels"]:
                        builder.diagnostic(
                            path + f"/{name}/{index}", label, "undeclared attribute label"
                        )
                        continue
                    builder.add(
                        kind="proposal",
                        semantic_type="attribute." + name,
                        item_key=path + f"/{name}/{index}",
                        value=source_value(content),
                        endpoints=(dict(role="mention", contribution_id=identity),),
                        reason=(
                            "attribute conditional on this decoded mention; "
                            "no independent cue is asserted"
                        ),
                        **_score(label),
                    )
    relations = raw.get("relation_extraction", {})
    if not isinstance(relations, dict):
        builder.diagnostic("relation_extraction", relations, "relation channel is not an object")
        relations = {}
    for predicate, values in relations.items():
        if predicate not in declaration.get("relations", ()) or not isinstance(values, list):
            builder.diagnostic(predicate, values, "undeclared relation or invalid population")
            continue
        for ordinal, value in enumerate(values):
            path = f"relations/{predicate}/{ordinal}"
            if not isinstance(value, Mapping):
                builder.diagnostic(path, value, "relation is not an object")
                continue
            endpoints = []
            unresolved = False
            for role in ("head", "tail"):
                endpoint = value.get(role)
                try:
                    if not isinstance(endpoint, Mapping):
                        raise GlinerRefused("relation endpoint has no source coordinates")
                    _map_returned_span(context, endpoint)
                    key = (endpoint["start"], endpoint["end"], endpoint["text"])
                    matches = located.get(key, ())
                except ContextRefused, GlinerRefused, KeyError, TypeError, ValueError:
                    matches = ()
                    unresolved = True
                if len(matches) == 1:
                    identity = matches[0]
                else:
                    identity = builder.field(
                        semantic_type="relation_endpoint",
                        item_key=path + "/" + role,
                        raw=endpoint,
                        locate=lambda endpoint=endpoint: _map_returned_span(context, endpoint),
                    )
                    unresolved |= len(matches) > 1
                endpoints.append(dict(role=role, contribution_id=identity))
            builder.add(
                kind="relation",
                semantic_type="relation." + predicate,
                item_key=path,
                endpoints=tuple(endpoints),
                value=source_value(value),
                disposition="unresolved" if unresolved else "candidate",
                reason=(
                    "native directed relation; endpoint reconciliation uses exact "
                    "coordinates, never equal-string order"
                ),
                **_score(value),
            )
    return builder.finish()


def _with_group_attachments(batch, *, schema_packs=None):
    """Private role associations from declared producer groups or captured geometry.

    Group membership supplies a proposal, never an independently observed relation
    or score. Missing or ambiguous primaries retain only their original composite.
    """
    from corpus_structure.semantic.contributions import contribution_identity, operation_identity

    supported = {
        "table": ("cell_value", {"row_label", "header_path", "unit", "note", "caption"}),
        "definition": ("term", {"alias", "defining_text"}),
        "assertion": (
            "predicate",
            {"subject", "object", "condition", "attribution", "quantification", "scope"},
        ),
    }
    packs, mismatched_packs = {}, {}
    for identity, declaration in (schema_packs or {}).items():
        pack = declaration if isinstance(declaration, GlinerPack) else GlinerPack(**declaration)
        if identity != pack.fingerprint:
            mismatched_packs[identity] = pack.fingerprint
            continue
        packs[identity] = json.loads(pack.declaration_json)
    by_id = {row["contribution_id"]: row for row in batch.contributions}
    by_operation = {row["operation_key"]: row for row in batch.operations}
    existing = {
        canonical_bytes([row["semantic_type"], row["endpoints"]])
        for row in batch.contributions
        if row["kind"] == "relation"
    }
    rows, operations = [], []
    for identity, actual in mismatched_packs.items():
        affected = [
            group["contribution_id"]
            for group in batch.contributions
            if group["kind"] == "composite"
            and group["semantic_type"].endswith(".returned_group")
            and "pack:" + identity
            in by_operation[group["operation_key"]]["computation_dependencies"]
        ]
        if not affected:
            continue
        refusal = dict(
            question="propose_returned_role_attachments",
            operation_version="retained-group-attachments-1",
            outcome="unsupported",
            inspected_count=0,
            emitted_count=0,
            inputs=(),
            reason=(
                "retained schema pack key differs from its exact declaration fingerprint; "
                "associations withheld"
            ),
            computation_dependencies=(
                "pack:" + identity,
                "actual-pack:" + actual,
                *("returned-group:" + group for group in affected),
            ),
        )
        refusal["operation_key"] = operation_identity(refusal)
        operations.append(refusal)
    for group in batch.contributions:
        if group["kind"] != "composite":
            continue
        native = group["semantic_type"].endswith(".native_group")
        suffix = ".native_group" if native else ".returned_group"
        if not group["semantic_type"].endswith(suffix):
            continue
        family = group["semantic_type"].removesuffix(suffix)
        if family not in supported:
            continue
        if family == "assertion" and native:
            # This proposal interprets the released extraction group, not co-location
            # within a different producer's native report.
            continue
        source_operation = by_operation[group["operation_key"]]
        primary_role, attachment_roles = supported[family]
        mode = "native_geometry" if native else None
        if native:
            if "producer:native_structure" not in source_operation["computation_dependencies"]:
                continue
        else:
            declarations = [
                packs[dependency.removeprefix("pack:")].get("structures", {}).get(family)
                for dependency in source_operation["computation_dependencies"]
                if dependency.startswith("pack:") and dependency.removeprefix("pack:") in packs
            ]
            declarations = [value for value in declarations if value is not None]
            if len(declarations) != 1:
                continue
            declaration = declarations[0]
            mode = declaration.get("mode")
            if mode not in {"natural", "latent"} or (
                mode == "natural" and declaration.get("anchor") != primary_role
            ):
                continue
        members = [by_id[identity] for identity in group["members"]]
        primaries = [
            row
            for row in members
            if row["kind"] == "proposal" and row["semantic_type"] == family + "." + primary_role
        ]
        if len(primaries) != 1 or not primaries[0]["anchors"]:
            continue
        primary = primaries[0]
        inspection = native and primary.get("anchor_role") == "inspection_subject"
        if not all(
            anchor["space"] == "native"
            and anchor["pin"] == group["pin"]
            and (anchor["precision"] == "exact" or (inspection and anchor["precision"] == "item"))
            for anchor in primary["anchors"]
        ):
            continue
        if not inspection and primary.get("anchor_role") == "inspection_subject":
            continue
        if family == "assertion" and primary.get("source_field_state", "present") != "present":
            continue
        if family == "table" and (
            len({anchor["pointer"] for anchor in primary["anchors"]}) != 1
            or "/data/table_cells/" not in primary["anchors"][0]["pointer"]
        ):
            continue
        targets = []
        for target in members:
            role = target["semantic_type"].removeprefix(family + ".")
            if (
                not target["semantic_type"].startswith(family + ".")
                or role not in attachment_roles
                or target["kind"] != "proposal"
                or not target["anchors"]
                or target.get("anchor_role") == "inspection_subject"
                or target.get("source_field_state", "present") != "present"
                or not all(
                    anchor["space"] == "native"
                    and anchor["pin"] == group["pin"]
                    and (
                        anchor["precision"] == "exact" or (native and anchor["precision"] == "item")
                    )
                    for anchor in target["anchors"]
                )
            ):
                continue
            endpoints = (
                dict(role=primary_role, contribution_id=primary["contribution_id"]),
                dict(role=role, contribution_id=target["contribution_id"]),
            )
            key = canonical_bytes([family + "." + role + "_attachment", endpoints])
            if key not in existing:
                targets.append((target, role, endpoints))
                existing.add(key)
        if not targets:
            continue
        dependencies = tuple(
            sorted(
                {
                    *source_operation["computation_dependencies"],
                    "derived-from-returned-group:" + source_operation["operation_key"],
                    "returned-group:" + group["contribution_id"],
                    "grouping-mode:" + str(mode),
                    "producer:derived_from_native_group"
                    if native
                    else "producer:derived_from_returned_group",
                }
            )
        )
        operation = dict(
            question="propose_returned_role_attachments",
            operation_version=(
                "retained-assertion-attachments-1"
                if family == "assertion"
                else "retained-group-attachments-1"
            ),
            outcome="succeeded",
            inspected_count=len(targets),
            emitted_count=len(targets),
            inputs=(),
            computation_dependencies=dependencies,
        )
        if source_operation.get("report_digest") is not None:
            operation["report_digest"] = source_operation["report_digest"]
        operation["operation_key"] = operation_identity(operation)
        operations.append(operation)
        for target, role, endpoints in targets:
            row = dict(
                contract="RetainedContributionSemantics",
                kind="relation",
                semantic_type=family + "." + role + "_attachment",
                operation_key=operation["operation_key"],
                item_key=target["item_key"] + "/attachment",
                pin=group["pin"],
                anchors=(),
                endpoints=endpoints,
                members=(),
                disposition="candidate",
                standing="retained_private",
                score_state="missing",
                reason="derived private association from declared " + str(mode) + " group roles; "
                "no independent relation evidence, truth or score",
                computation_dependencies=dependencies,
            )
            row["contribution_id"] = contribution_identity(row)
            rows.append(row)
    return ContributionBatch.combine((batch, ContributionBatch(tuple(operations), tuple(rows))))


def _with_returned_attachments(batch, context, *, pack, item_key):
    return _with_group_attachments(batch, schema_packs={pack.fingerprint: pack})


def adapt_native_groups(context, *, family, groups, item_key, dependencies=()):
    """Native geometry/structural proposals have native attribution, never model scores."""
    raw = [asdict(group) for group in groups]
    builder = _Builder(
        context,
        report_digest=_digest(raw),
        computation=_digest([family, raw]),
        producer="native_structure",
        item_key=item_key,
        dependencies=dependencies,
    )
    for group_index, group in enumerate(groups):
        group_path = f"native:{family}[{group_index}]"
        members = []
        for index, field in enumerate(group.fields):
            path = f"{group_path}.fields[{index}]"
            anchors = []
            if field.native_pointer is not None:
                try:
                    anchors.append(native_item_anchor(context, field.native_pointer))
                except ContextRefused as error:
                    members.append(builder.diagnostic(path, asdict(field), str(error)))
                    continue
            else:
                try:
                    for span in field.spans:
                        for piece in context.map_span(
                            span.start, span.end, literal=span.text, allow_multiple=True
                        ):
                            anchor, coordinate = evidence_anchor(context, piece, native=True)
                            anchors.append(anchor)
                            builder.coordinates[
                                canonical_bytes(
                                    {k: v for k, v in coordinate.items() if k != "text"}
                                )
                            ] = coordinate
                except ContextRefused as error:
                    anchors = []
                    members.append(
                        builder.diagnostic(path + "/location", asdict(field), str(error))
                    )
            inspection_subject = field.state != "present" and bool(
                field.inspected_pointer or field.inspected_spans
            )
            if inspection_subject:
                try:
                    if field.inspected_pointer:
                        anchors = [native_item_anchor(context, field.inspected_pointer)]
                    else:
                        anchors = []
                        for span in field.inspected_spans:
                            for piece in context.map_span(
                                span.start, span.end, literal=span.text, allow_multiple=True
                            ):
                                anchor, coordinate = evidence_anchor(context, piece, native=True)
                                anchors.append(anchor)
                                builder.coordinates[
                                    canonical_bytes(
                                        {k: v for k, v in coordinate.items() if k != "text"}
                                    )
                                ] = coordinate
                except ContextRefused as error:
                    anchors = []
                    members.append(
                        builder.diagnostic(path + "/inspection", asdict(field), str(error))
                    )
            builder.operation["inspected_count"] += 1
            occurrence = None
            if anchors and not inspection_subject:
                occurrence = builder.add(
                    kind="occurrence",
                    semantic_type="source_occurrence",
                    item_key=path + "/occurrence",
                    anchors=anchors,
                )
            members.append(
                builder.add(
                    kind="proposal",
                    semantic_type=family + "." + field.role,
                    item_key=path,
                    anchors=anchors,
                    value=source_value(asdict(field)),
                    source_field_state=field.state,
                    anchor_role="inspection_subject" if inspection_subject else "evidence",
                    endpoints=(dict(role="occurrence", contribution_id=occurrence),)
                    if occurrence
                    else (),
                    reason=field.reason or group.reason,
                )
            )
        builder.add(
            kind="composite",
            semantic_type=family + ".native_group",
            item_key=group_path,
            members=tuple(members),
            reason=group.reason,
        )
    return _with_group_attachments(builder.finish())


def _restore_pin(row):
    from corpus_structure.semantic.product_reference import ProductReference
    from corpus_structure.semantic.source_contexts import NativeSourcePin

    row = dict(row)
    row["native_product"] = ProductReference(**row["native_product"])
    return NativeSourcePin(**row)


def reconstruct_context(reader, view, details, index, *, expected_digest, bounds=None):
    """Rebuild an archived selection and require its full original context digest.

    Old selections did not archive context bounds/version. Only digest-equal historical
    defaults are admissible; a different configuration stays explicitly unavailable.
    New manifests retain those inputs directly. No routing/annotation/model is rerun.
    """
    from corpus_structure.semantic.proposals import native_source_frame
    from corpus_structure.semantic.source_contexts import (
        ContextRelationship,
        ContextRetrieval,
        PreparedNativeSources,
        RelatedNativeSource,
        RetrievalOutcome,
        SourceSlice,
        SyntheticText,
    )

    selection = details["contexts"][index]
    primary = native_source_frame(view, ())
    related = tuple(
        RelatedNativeSource(
            native_source_frame(reader.source_view(identity), ()),
            ContextRelationship(relationship),
            reason,
        )
        for identity, relationship, reason in selection.get("relationships", ())
    )
    pieces = tuple(
        SourceSlice(**piece) if "source_view_id" in piece else SyntheticText(**piece)
        for piece in selection.get("pieces", ())
    ) or (SourceSlice(primary.source_view_id, selection["start"], selection["end"]),)
    retrievals = tuple(
        ContextRetrieval(
            relationship=ContextRelationship(row["relationship"]),
            reason=row["reason"],
            scope_ref=row["scope_ref"],
            membership_digest=row["membership_digest"],
            outcome=RetrievalOutcome(row["outcome"]),
            candidates=tuple(_restore_pin(pin) for pin in row["candidates"]),
            selected=tuple(row["selected"]),
            excluded=tuple(row["excluded"]),
            terminal_reason=row["terminal_reason"],
        )
        for row in selection.get("retrievals", ())
    )
    manifest = details.get("context_manifests", {}).get(str(index))
    if manifest:
        options = (manifest,)
    else:
        bound = bounds or dict(max_chars=2048, max_pieces=64, max_sources=16)
        options = ({**bound, "version": 2}, {**bound, "version": 1})
    for option in options:
        version = option["version"]
        context = NativeSourceContext(
            primary,
            related,
            pieces,
            ",".join(selection["families"]),
            details["policy"],
            selection["reason"],
            retrievals=retrievals,
            max_chars=option["max_chars"],
            max_pieces=option["max_pieces"],
            max_sources=option.get("max_sources", 16),
            version=version,
            preparation=PreparedNativeSources((primary, *(entry.source for entry in related)))
            if version == 2
            else None,
        )
        if context.dependency_digest == expected_digest:
            return context
    raise GlinerRefused(
        "retained source context/preparation is unavailable: context digest differs"
    )


def replay_retained_contributions(
    reader,
    view,
    upstream,
    *,
    schema_packs=None,
    context_bounds=None,
) -> ContributionBatch:
    """The registered retained-reading operation's raw-report consumer.

    Missing context/profile/schema has an operation outcome with no fabricated source
    evidence. Failed producer calls do not erase other already returned report products.
    """
    from corpus_structure.semantic.contributions import operation_identity

    from .record_assembly import LiteralSpan, NativeRecordGroup, RoleInput

    details = upstream["parse_detail"]
    packs = dict(schema_packs or {})
    packs.update(details.get("schema_packs", {}))
    if (
        upstream.get("contributions") is not None
        and upstream.get("contribution_operations") is not None
    ):
        # These sealed typed products own their meaning and outcome/version. Do not
        # reconstruct a narrower population by visiting only old record reports.
        def restore(class_name, raw):
            restored = reader.prepared.validate_json(class_name, canonical_bytes(raw)).model_dump(
                mode="python"
            )
            if canonical_bytes(restored) != canonical_bytes(raw):
                raise GlinerRefused(
                    "sealed typed product changes canonical bytes under its released decoder"
                )
            return restored

        original = ContributionBatch(
            tuple(
                restore("SourceContributionOperation", row)
                for row in upstream["contribution_operations"]
            ),
            tuple(restore("SourceContribution", row) for row in upstream["contributions"]),
            tuple(
                restore("RecordCoordinateText", row)
                for row in upstream.get("contribution_coordinate_texts") or ()
            ),
        )
        return _with_group_attachments(original, schema_packs=packs)
    batches, contexts = [], {}
    dependencies = ("retained-result:" + _digest(upstream),)
    for index, entry in enumerate(details.get("reports", ())):
        retained = entry.get("report")
        key = f"retained/reports[{index}]"
        try:
            context_index = entry["context"]
            expected = retained["context_digest"] if retained else entry.get("context_digest")
            if expected is None:
                expected = next(
                    row["report"]["context_digest"]
                    for row in details["reports"]
                    if row.get("context") == context_index and "report" in row
                )
            cache_key = (context_index, expected)
            if cache_key not in contexts:
                contexts[cache_key] = reconstruct_context(
                    reader,
                    view,
                    details,
                    context_index,
                    expected_digest=expected,
                    bounds=context_bounds,
                )
            context = contexts[cache_key]
            if retained:
                report = restore_report(retained, context, details.get("effective_profiles", {}))
                declared = packs.get(report.pack)
                if declared is None:
                    raise GlinerRefused(
                        "retained schema pack is unavailable; supply its exact declaration"
                    )
                pack = declared if isinstance(declared, GlinerPack) else GlinerPack(**declared)
                batches.append(
                    adapt_report(
                        report, context, pack=pack, item_key=key, dependencies=dependencies
                    )
                )
            elif entry.get("operation") == "native_structure":
                groups = tuple(
                    NativeRecordGroup(
                        fields=tuple(
                            RoleInput(
                                role=field["role"],
                                spans=tuple(LiteralSpan(**span) for span in field.get("spans", ())),
                                native_pointer=field.get("native_pointer"),
                                label=field.get("label"),
                                cues=tuple(LiteralSpan(**span) for span in field.get("cues", ())),
                                state=field.get("state", "present"),
                                reason=field.get("reason", ""),
                                inspected_pointer=field.get("inspected_pointer"),
                                inspected_spans=tuple(
                                    LiteralSpan(**span) for span in field.get("inspected_spans", ())
                                ),
                                decimal=field.get("decimal", False),
                                dependencies=tuple(field.get("dependencies", ())),
                            )
                            for field in group["fields"]
                        ),
                        reason=group["reason"],
                        dependencies=tuple(group.get("dependencies", ())),
                    )
                    for group in entry.get("groups", ())
                )
                batches.append(
                    adapt_native_groups(
                        context,
                        family=entry["family"],
                        groups=groups,
                        item_key=key,
                        dependencies=dependencies,
                    )
                )
            else:
                raise GlinerRefused(entry.get("reason", "producer returned no raw report"))
        except (
            GlinerRefused,
            ContextRefused,
            KeyError,
            TypeError,
            ValueError,
            StopIteration,
        ) as error:
            operation = dict(
                question="recover_returned_local_contributions",
                operation_version=ADAPTER_VERSION,
                outcome="unsupported",
                inspected_count=0,
                emitted_count=0,
                report_digest=_digest(retained or entry),
                inputs=(),
                reason=str(error) or "retained source context is unavailable",
                computation_dependencies=dependencies,
            )
            operation["operation_key"] = operation_identity({**operation, "item_key": key})
            batches.append(ContributionBatch((operation,)))
    return ContributionBatch.combine(batches)


def replay_historical_contributions(reader, current_view, retained):
    """Explicit successor derivation, retaining original report and coordinate identities."""
    from types import SimpleNamespace

    from corpus_structure.semantic.contributions import (
        contribution_identity,
        occurrence_identity,
        operation_identity,
    )
    from corpus_structure.semantic.proposals import native_source_frame
    from corpus_structure.semantic.record_contracts import anchor_identity

    from .m1_source import configured_pack_variants

    originals = {view.ref.id: view for view in retained.source_views}
    source_id = retained.result["parse_detail"]["source_pin"]["source_view_id"]
    detached = SimpleNamespace(prepared=retained.prepared, source_view=originals.__getitem__)
    config = SimpleNamespace(**retained.configuration)
    variants = configured_pack_variants(retained.prepared, config)
    packs = {pack.fingerprint: pack for group in variants.values() for _, _, pack in group}
    original = replay_retained_contributions(
        detached,
        originals[source_id],
        retained.result,
        schema_packs=packs,
        context_bounds=dict(
            max_chars=config.max_context_chars, max_pieces=config.max_context_pieces, max_sources=16
        ),
    )
    mappings = {}
    for binding in retained.source_bindings:
        old = originals[binding["original_source_view_id"]]
        new = reader.source_view(binding["current_source_view_id"])
        mappings[old.ref.id] = (
            record_source_pin(native_source_frame(old, ())),
            record_source_pin(native_source_frame(new, ())),
        )
    if mappings[source_id][1]["source_view_id"] != current_view.ref.id:
        raise GlinerRefused("historical primary does not correspond to the current source")
    map_digest = _digest(retained.source_bindings)
    provenance = (
        f"retained-task:{retained.task_id}:{retained.body_digest}",
        "retained-source-map:" + map_digest,
        "retained-release:" + retained.release_id,
    )
    operations, operation_keys = [], {}
    for old in original.operations:
        operation: dict[str, Any] = dict(
            old,
            retained_task_id=retained.task_id,
            retained_result_digest=retained.body_digest,
            retained_source_bindings=retained.source_bindings,
            computation_dependencies=tuple(
                sorted(
                    {
                        *old["computation_dependencies"],
                        *provenance,
                        "predecessor-operation:" + old["operation_key"],
                    }
                )
            ),
        )
        operation["operation_key"] = operation_identity(operation)
        operation_keys[old["operation_key"]] = operation["operation_key"]
        operations.append(operation)

    def pin(original_pin):
        pair = mappings.get(original_pin["source_view_id"])
        if pair is None or pair[0] != original_pin:
            raise GlinerRefused(
                "historical contribution has no authenticated source correspondence"
            )
        return pair[1]

    identities, rows = {}, []
    for old in original.contributions:
        anchors = []
        for original_anchor in old["anchors"]:
            anchor: dict[str, Any] = dict(original_anchor, pin=pin(original_anchor["pin"]))
            anchor["anchor_id"] = anchor_identity(anchor)
            anchors.append(anchor)
        row: dict[str, Any] = dict(
            old,
            pin=pin(old["pin"]),
            anchors=tuple(anchors),
            operation_key=operation_keys[old["operation_key"]],
            endpoints=tuple(
                dict(endpoint, contribution_id=identities[endpoint["contribution_id"]])
                for endpoint in old["endpoints"]
            ),
            members=tuple(identities[identity] for identity in old["members"]),
            computation_dependencies=tuple(
                sorted(
                    {
                        *old["computation_dependencies"],
                        *provenance,
                        "predecessor-contribution:" + old["contribution_id"],
                    }
                )
            ),
        )
        if anchors:
            row["occurrence_id"] = occurrence_identity(anchors)
        row["contribution_id"] = contribution_identity(row)
        identities[old["contribution_id"]] = row["contribution_id"]
        rows.append(row)
    coordinates = tuple(
        dict(coordinate, pin=pin(coordinate["pin"])) for coordinate in original.coordinate_texts
    )
    return ContributionBatch(tuple(operations), tuple(rows), coordinates)
