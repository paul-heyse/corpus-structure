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


def _with_returned_attachments(batch, context, *, pack, item_key):
    """Explicit derived questions supported by the released natural-group roles.

    The decoder did not return a relation head or an independent attachment score.
    These private candidates retain that distinction and refer to the actual field
    proposals. Missing/ambiguous primaries retain only the original group membership.
    """
    declarations = json.loads(pack.declaration_json).get("structures", {})
    supported = {
        "table": ("cell_value", {"row_label", "header_path", "unit", "note", "caption"}),
        "definition": ("term", {"alias", "defining_text"}),
    }
    by_id = {row["contribution_id"]: row for row in batch.contributions}
    derived = _Builder(
        context,
        report_digest=batch.operations[0]["report_digest"],
        computation=batch.operations[0]["operation_key"],
        producer="derived_from_returned_group",
        item_key=item_key + "/attachments",
        dependencies=("derived-from-returned-group:" + batch.operations[0]["operation_key"],),
        question="propose_returned_role_attachments",
        operation_version="retained-group-attachments-1",
    )
    has_supported_group = False
    for group in batch.contributions:
        if group["kind"] != "composite":
            continue
        family = group["semantic_type"].removesuffix(".returned_group")
        if family not in supported or family not in declarations:
            continue
        primary_role, attachment_roles = supported[family]
        declaration = declarations[family]
        if declaration.get("mode") != "natural" or declaration.get("anchor") != primary_role:
            continue
        has_supported_group = True
        members = [by_id[identity] for identity in group["members"]]
        primaries = [row for row in members if row["semantic_type"] == family + "." + primary_role]
        if len(primaries) != 1 or not primaries[0]["anchors"]:
            continue
        primary = primaries[0]
        if not all(
            anchor["space"] == "native"
            and anchor["precision"] == "exact"
            and anchor["pin"] == record_source_pin(context.primary)
            for anchor in primary["anchors"]
        ):
            continue
        if family == "table" and (
            len({anchor["pointer"] for anchor in primary["anchors"]}) != 1
            or "/data/table_cells/" not in primary["anchors"][0]["pointer"]
        ):
            continue
        for target in members:
            role = target["semantic_type"].removeprefix(family + ".")
            if (
                role not in attachment_roles
                or target["kind"] != "proposal"
                or not target["anchors"]
            ):
                continue
            derived.operation["inspected_count"] += 1
            derived.add(
                kind="relation",
                semantic_type=family + "." + role + "_attachment",
                item_key=target["item_key"] + "/attachment",
                endpoints=(
                    dict(role=primary_role, contribution_id=primary["contribution_id"]),
                    dict(role=role, contribution_id=target["contribution_id"]),
                ),
                reason="derived candidate from released natural-group role semantics; "
                "no independent relation-head output or attachment score",
                computation_dependencies=(
                    *derived.operation["computation_dependencies"],
                    "returned-group:" + group["contribution_id"],
                ),
            )
    if not has_supported_group:
        return batch
    return ContributionBatch.combine((batch, derived.finish()))


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
            builder.operation["inspected_count"] += 1
            occurrence = None
            if anchors:
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
    return builder.finish()


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
