"""Private candidate composition over released roles and genuine source coordinates.

Small native groups are composed directly. This module performs no corpus retrieval,
pairwise matching, inference, publication or acceptance. Grouping is a producer proposal.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any

from pydantic import BaseModel

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.record_contracts import (
    anchor_identity,
    bind_record_candidates,
    evidence_set_identity,
    interpretation_identity,
    record_identity,
)
from corpus_structure.semantic.source_contexts import (
    ContextRefused,
    NativeSourceContext,
    NativeSourcePin,
    SourceInterval,
)
from corpus_structure.semantic.types import PreparedRelease

from .gliner import GlinerPack, GlinerRefused, GlinerReport, map_literal, map_record_field
from .math.pdf import FormulaOccurrence
from .record_packs import classification, family_roles, field_kind


@dataclass(frozen=True)
class LiteralSpan:
    """A separately addressed literal in serialized context character coordinates."""

    start: int
    end: int
    text: str


@dataclass(frozen=True)
class RoleInput:
    """Explicit structural reading, not another editable family declaration.

    Multiple spans preserve ordered literal pieces (headers and discontinuous text).
    Classification cues are supplied independently of any decoder enum offsets.
    Nonpresent readings require a reason and an explicitly located inspected scope.
    Dependencies include note inheritance, rejected alternatives and inspection policy.
    """

    role: str
    spans: tuple[LiteralSpan, ...] = ()
    native_pointer: str | None = None
    label: str | None = None
    cues: tuple[LiteralSpan, ...] = ()
    state: str = "present"
    reason: str = ""
    inspected_pointer: str | None = None
    decimal: bool = False
    dependencies: tuple[str, ...] = ()


@dataclass(frozen=True)
class NativeRecordGroup:
    fields: tuple[RoleInput, ...]
    reason: str
    dependencies: tuple[str, ...] = ()


@dataclass(frozen=True)
class AssemblyDiagnostic:
    group: int
    role: str | None
    code: str
    reason: str


@dataclass(frozen=True)
class AssemblyResult:
    records: tuple[BaseModel, ...]
    diagnostics: tuple[AssemblyDiagnostic, ...]
    coordinate_texts: tuple[dict[str, Any], ...]
    dependencies: tuple[str, ...]
    raw_report: GlinerReport | None
    native_groups: tuple[NativeRecordGroup, ...] = ()


def _digest(kind: str, value: Any) -> str:
    return kind + ":" + sha256(canonical_bytes(value)).hexdigest()


def _pin(context: NativeSourceContext) -> dict[str, Any]:
    source = context.primary
    product = source.native_product
    return dict(
        source=source.unit_ref,
        native_product_task_id=product.task_id,
        product_key=product.product_key,
        product_digest=product.content_digest,
        projection_digest=source.projection_digest,
        recipe_digest=source.recipe_digest,
        source_view_id=source.source_view_id,
    )


def _native_pointers(context: NativeSourceContext) -> set[str]:
    native = json.loads(context.primary.native_context)
    pointers = set()
    for item in (*native["items"], *native["ancestors"]):
        pointer = item.get("self_ref", item.get("pointer"))
        pointers.add(pointer)
        for index, _ in enumerate(item.get("data", {}).get("table_cells", ())):
            pointers.add(f"{pointer}/data/table_cells/{index}")
    for piece in native["pieces"]:
        if piece.get("source_field") == "cell_text" and piece.get("cell_index") is not None:
            pointers.add(f"{piece['item_ref']}/data/table_cells/{piece['cell_index']}")
    return pointers


def _assemble(
    prepared: PreparedRelease,
    context: NativeSourceContext,
    *,
    contract: str,
    occurrence_roles: tuple[str, ...],
    policy_version: str,
    groups: Sequence[Mapping[str, Any]],
    supplements: Mapping[int, NativeRecordGroup],
    pack: GlinerPack | None,
    report: GlinerReport | None,
) -> AssemblyResult:
    definition, roles = family_roles(prepared, contract)
    role_names = {role.name for role in roles}
    if not policy_version or not occurrence_roles or not set(occurrence_roles) <= role_names:
        raise GlinerRefused("assembly requires policy and released occurrence anchor roles")
    if len(set(occurrence_roles)) != len(occurrence_roles):
        raise GlinerRefused("duplicate occurrence roles")
    if set(supplements) - set(range(len(groups))):
        raise GlinerRefused("supplement names an absent native group")
    properties = {prop.name: prop for prop in definition.properties}
    family = properties["family"].equals_string
    if not family:
        raise GlinerRefused("released family identifier is missing")
    pin = _pin(context)
    primary_pin = NativeSourcePin.from_source(context.primary)
    pointers = _native_pointers(context)
    diagnostics: list[AssemblyDiagnostic] = []
    coordinates: dict[tuple[str, str], dict[str, Any]] = {}
    dependencies = {
        "release:" + prepared.release_id,
        "context:" + context.dependency_digest,
        "assembly-policy:" + policy_version,
    }
    if report is not None:
        dependencies.update(
            ("computation:" + report.computation, _digest("raw-report", asdict(report)))
        )
    # Per-group explicit inputs remain in computation dependencies, including rejected choices.
    dependencies.update(
        _digest("structural-input", [index, asdict(group)]) for index, group in supplements.items()
    )
    all_dependencies = set(dependencies)
    records: list[dict[str, Any]] = []
    for index, group in enumerate(groups):
        supplement = supplements.get(index, NativeRecordGroup((), "native decoder proposal"))
        if not supplement.reason.strip():
            raise GlinerRefused("structural group requires its attachment/inspection reason")
        explicit = {field.role: field for field in supplement.fields}
        if len(explicit) != len(supplement.fields) or set(explicit) - role_names:
            raise GlinerRefused("duplicate or unreleased structural role")
        group_dependencies = set(dependencies) | set(supplement.dependencies)
        anchors: dict[str, dict[str, Any]] = {}
        evidence_sets: dict[str, dict[str, Any]] = {}
        fields = []
        role_anchors: dict[str, tuple[str, ...]] = {}

        def native_anchor(pointer: str, _anchors=anchors) -> dict[str, Any]:
            if pointer not in pointers:
                raise GlinerRefused("native pointer is outside the explicitly retained source view")
            row: dict[str, Any] = dict(pin=pin, space="native", pointer=pointer, precision="item")
            row["anchor_id"] = anchor_identity(row)
            _anchors[row["anchor_id"]] = row
            return row

        def literal_anchors(
            spans: tuple[LiteralSpan, ...], role: str, *, cue=False, _anchors=anchors
        ) -> list[dict[str, Any]]:
            mapped: list[dict[str, Any]] = []
            for span in spans:
                raw = asdict(span)
                if report is not None and pack is not None:
                    pieces = (
                        map_literal(report, context, raw, allow_multiple=True)
                        if cue
                        else map_record_field(
                            pack, family, role, report, context, raw, allow_multiple=True
                        )
                    )
                else:
                    pieces = context.map_span(
                        span.start, span.end, literal=span.text, allow_multiple=True
                    )
                for piece in pieces:
                    if piece.source != primary_pin:
                        raise GlinerRefused(
                            "related/cross-view evidence is unsupported by private record custody"
                        )
                    if piece.source_field not in {None, "text", "orig", "cell_text"}:
                        raise GlinerRefused(
                            "alternate/recognized source space is unsupported by this assembler"
                        )
                    pointer = json.loads(piece.item_locator.removeprefix("pdf:"))["pointer"]
                    if piece.cell_index is not None:
                        pointer += f"/data/table_cells/{piece.cell_index}"
                    row = dict(
                        pin=pin,
                        space="selected_projection",
                        pointer=pointer,
                        precision="exact",
                        start=piece.start,
                        end=piece.end,
                        source_piece=piece.quote,
                    )
                    row["anchor_id"] = anchor_identity(row)
                    _anchors[row["anchor_id"]] = row
                    coordinates[("selected_projection", pointer)] = dict(
                        pin=pin,
                        space="selected_projection",
                        pointer=pointer,
                        text=context.primary.text,
                    )
                    mapped.append(row)
            # A role's ordered source pieces may not overlap or reverse a coordinate.
            ends: dict[str, int] = {}
            for row in mapped:
                if row["start"] < ends.get(row["pointer"], 0):
                    raise GlinerRefused("literal pieces overlap or reverse their source order")
                ends[row["pointer"]] = row["end"]
            return mapped

        for role in roles:
            kind = field_kind(prepared, role)
            role_type = prepared.index.definitions[role.range]
            field: dict[str, Any] = dict(
                role=role.name,
                kind=kind,
                state="unresolved",
                meaning_changing="MeaningChangingRecordField" in role_type.ancestors,
                evidence_status="unavailable",
                reason="decoder field absent; source meaning remains unresolved",
            )
            supplied = explicit.get(role.name)
            raw = group.get(role.name)
            try:
                pieces = []
                usage = "literal"
                if supplied is not None:
                    group_dependencies.update(supplied.dependencies)
                    if kind != "literal" and (supplied.spans or supplied.decimal):
                        raise GlinerRefused(
                            "nonliteral structural role cannot claim literal values"
                        )
                    if kind != "classified" and (supplied.label is not None or supplied.cues):
                        raise GlinerRefused("nonclassified role cannot claim classification values")
                    if kind != "native" and supplied.native_pointer is not None:
                        raise GlinerRefused("nonnative role cannot claim a native location value")
                    if supplied.state != "present":
                        if (
                            supplied.spans
                            or supplied.native_pointer
                            or supplied.label
                            or supplied.cues
                        ):
                            raise GlinerRefused("nonpresent reading cannot carry an actual value")
                        if not supplied.reason.strip() or not supplied.inspected_pointer:
                            raise GlinerRefused(
                                "nonpresent reading requires an inspected scope and reason"
                            )
                        pieces = [native_anchor(supplied.inspected_pointer)]
                        field.update(state=supplied.state, reason=supplied.reason)
                        usage = "context"
                    elif kind == "native":
                        if not supplied.native_pointer:
                            raise GlinerRefused("native role requires its actual native pointer")
                        pieces = [native_anchor(supplied.native_pointer)]
                        field.update(
                            state="present",
                            value=dict(kind="native_location", pointer=supplied.native_pointer),
                        )
                        usage = "native"
                    elif kind == "literal":
                        if not supplied.spans:
                            raise GlinerRefused(
                                "literal role requires nonempty located source pieces"
                            )
                        pieces = literal_anchors(supplied.spans, role.name)
                        originals = tuple(piece["source_piece"] for piece in pieces)
                        field.update(state="present")
                        if len(originals) == 1:
                            original = originals[0]
                            field.update(
                                original=original,
                                value=dict(kind="decimal", lexical=original)
                                if supplied.decimal
                                else dict(kind="text", text=original),
                            )
                        else:
                            field.update(
                                original_pieces=originals,
                                value=dict(kind="text_sequence", items=originals),
                            )
                    elif kind == "classified":
                        label = supplied.label
                        value_kind, choices = classification(prepared, role)
                        if label not in choices:
                            raise GlinerRefused(
                                "classification label differs from released vocabulary"
                            )
                        if supplied.cues and not supplied.reason.strip():
                            raise GlinerRefused(
                                "classification cue requires an explicit scope/association reason"
                            )
                        pieces = literal_anchors(supplied.cues, role.name, cue=True)
                        field.update(state="present", value=dict(kind=value_kind, label=label))
                        if not pieces:
                            field["reason"] = (
                                "classification candidate has no independently located source cue"
                            )
                        usage = "classification_cue"
                    else:
                        raise GlinerRefused(
                            "normalization/derivation requires a separate declared operation"
                        )
                elif raw is not None and kind == "literal":
                    if not isinstance(raw, dict):
                        raise GlinerRefused("literal decoder field lacks source coordinates")
                    start, end, text = raw.get("start"), raw.get("end"), raw.get("text")
                    if type(start) is not int or type(end) is not int or not isinstance(text, str):
                        raise GlinerRefused("literal decoder field lacks typed source coordinates")
                    pieces = literal_anchors((LiteralSpan(start, end, text),), role.name)
                    original = "".join(piece["source_piece"] for piece in pieces)
                    field.update(
                        state="present", original=original, value=dict(kind="text", text=original)
                    )
                elif raw is not None and kind == "classified":
                    label = raw.get("text", raw.get("label")) if isinstance(raw, dict) else raw
                    value_kind, choices = classification(prepared, role)
                    if label not in choices:
                        raise GlinerRefused("classification label differs from released vocabulary")
                    field.update(
                        state="present",
                        value=dict(kind=value_kind, label=label),
                        reason=(
                            "native classification candidate; "
                            "enum offsets are not source cue evidence"
                        ),
                    )
                if pieces:
                    ids = tuple(piece["anchor_id"] for piece in pieces)
                    evidence = dict(role=role.name, usage=usage, ordering="ordered", anchors=ids)
                    evidence["set_id"] = evidence_set_identity(evidence)
                    evidence_sets[evidence["set_id"]] = evidence
                    field.update(evidence_status="available", evidence_sets=(evidence["set_id"],))
                    if field["state"] == "present":
                        role_anchors[role.name] = ids
                if field["state"] == "present" and field.get("evidence_status") == "available":
                    field.pop("reason", None)
                # Validate against the released role, including specialized classification values.
                prepared.validate_python(role.range, field)
            except (ValueError, TypeError, KeyError, ContextRefused) as error:
                diagnostics.append(
                    AssemblyDiagnostic(index, role.name, "unsupported_field", str(error))
                )
                field = dict(
                    role=role.name,
                    kind=kind,
                    state="unresolved",
                    meaning_changing="MeaningChangingRecordField" in role_type.ancestors,
                    evidence_status="unavailable",
                    reason=str(error),
                )
                role_anchors.pop(role.name, None)
            if field["state"] == "unresolved":
                diagnostics.append(
                    AssemblyDiagnostic(index, role.name, "unresolved_field", field["reason"])
                )
            fields.append(field)
        all_dependencies.update(group_dependencies)
        if any(role not in role_anchors for role in occurrence_roles):
            diagnostics.append(
                AssemblyDiagnostic(
                    index,
                    None,
                    "unlocated_occurrence",
                    "canonical occurrence role is not independently located",
                )
            )
            continue
        occurrence = tuple(
            dict.fromkeys(anchor for role in occurrence_roles for anchor in role_anchors[role])
        )
        row = dict(
            contract=contract,
            family=family,
            occurrence_recipe=properties["occurrence_recipe"].equals_string,
            pin=pin,
            occurrence_anchors=occurrence,
            standing="candidate",
            policy_version=policy_version,
            fields=tuple(fields),
            anchors=tuple(anchors.values()),
            evidence_sets=tuple(evidence_sets.values()),
            computation_dependencies=tuple(sorted(group_dependencies)),
        )
        row["record_id"] = record_identity(prepared.release_id, row)
        row["interpretation_id"] = interpretation_identity(row)
        records.append(row)
    # Exact duplicate native groups are observations of the same interpretation, not votes.
    unique = {(row["record_id"], row["interpretation_id"]): row for row in records}
    bound = bind_record_candidates(
        prepared,
        source=context.primary.unit_ref,
        records=tuple(unique.values()),
        coordinate_texts=tuple(coordinates.values()),
    )
    return AssemblyResult(
        bound,
        tuple(diagnostics),
        tuple(coordinates.values()),
        tuple(sorted(all_dependencies)),
        report,
        tuple(supplements.values()),
    )


def assemble_records(
    prepared: PreparedRelease,
    context: NativeSourceContext,
    pack: GlinerPack,
    report: GlinerReport,
    *,
    contract: str,
    anchor_role: str,
    policy_version: str,
    occurrence_roles: tuple[str, ...] | None = None,
    supplements: Mapping[int, NativeRecordGroup] | None = None,
) -> AssemblyResult:
    """Bind an actual native combined report; never reinterpret a foreign pack or context."""
    if pack.release != prepared.release_id or report.pack != pack.fingerprint:
        raise GlinerRefused("report/pack differs from the prepared semantic release")
    if (
        report.context_id != context.dependency_digest
        or report.context_digest != context.dependency_digest
    ):
        raise GlinerRefused("report belongs to another source context")
    if report.preparation.consumed_text != context.text + report.preparation.synthetic_suffix:
        raise GlinerRefused("provider preprocessing changed the source prefix")
    if report.preparation.synthetic_suffix not in {"", "."}:
        raise GlinerRefused("unsupported provider synthetic suffix")
    if not report.computation or not report.profile:
        raise GlinerRefused("report requires its computation and execution profile dependencies")
    pack.compile()
    definition, roles = family_roles(prepared, contract)
    family = next(prop.equals_string for prop in definition.properties if prop.name == "family")
    if not family:
        raise GlinerRefused("released family identifier is missing")
    structure = json.loads(pack.declaration_json)["structures"][family]
    if structure["anchor"] != anchor_role or structure["mode"] != "natural":
        raise GlinerRefused("pack grouping anchor differs from the explicit profile")
    declared = {field["name"]: field for field in structure["fields"]}
    expected = {
        role.name for role in roles if field_kind(prepared, role) in {"literal", "classified"}
    }
    if set(declared) != expected or len(declared) != len(structure["fields"]):
        raise GlinerRefused("pack fields differ from released literal/classified roles")
    for role in roles:
        if role.name in declared:
            if (
                declared[role.name].get("dtype") != "str"
                or declared[role.name].get("cardinality") != "optional_one"
            ):
                raise GlinerRefused("pack requires optional_one literal/classified string fields")
            choices = declared[role.name].get("choices", ())
            expected_choices = (
                classification(prepared, role)[1]
                if field_kind(prepared, role) == "classified"
                else ()
            )
            if tuple(sorted(choices)) != expected_choices:
                raise GlinerRefused("pack choices differ from released classification")
    raw = report.raw
    if not isinstance(raw, dict):
        raise GlinerRefused("native combined report must be an object")
    groups = raw.get(family, [])
    if not isinstance(groups, list) or any(not isinstance(group, dict) for group in groups):
        raise GlinerRefused("native report family output is not grouped records")
    if any(set(group) - expected - {"confidence"} for group in groups):
        raise GlinerRefused("native report group names fields outside its released family pack")
    return _assemble(
        prepared,
        context,
        contract=contract,
        occurrence_roles=occurrence_roles or (anchor_role,),
        policy_version=policy_version,
        groups=groups,
        supplements=supplements or {},
        pack=pack,
        report=report,
    )


def assemble_native_records(
    prepared: PreparedRelease,
    context: NativeSourceContext,
    *,
    contract: str,
    occurrence_roles: tuple[str, ...],
    policy_version: str,
    groups: tuple[NativeRecordGroup, ...],
) -> AssemblyResult:
    """Compose actual native table/formula/inspection groups without inventing inference."""
    return _assemble(
        prepared,
        context,
        contract=contract,
        occurrence_roles=occurrence_roles,
        policy_version=policy_version,
        groups=tuple({} for _ in groups),
        supplements=dict(enumerate(groups)),
        pack=None,
        report=None,
    )


def _item_spans(
    context: NativeSourceContext, pointer: str, *, cell_index: int | None = None
) -> tuple[LiteralSpan, ...]:
    """Lift retained native piece positions, never search equal source strings."""
    primary_pin = NativeSourcePin.from_source(context.primary)
    return tuple(
        LiteralSpan(row.model_start, row.model_end, context.text[row.model_start : row.model_end])
        for row in context.intervals
        if isinstance(row, SourceInterval)
        and row.source == primary_pin
        and json.loads(row.item_locator.removeprefix("pdf:"))["pointer"] == pointer
        and row.cell_index == cell_index
    )


def native_table_groups(
    context: NativeSourceContext,
    *,
    table_pointer: str,
    cells: tuple[int, ...],
    row_paths: Mapping[int, tuple[int, ...]],
    header_paths: Mapping[int, tuple[int, ...]],
    inherited: Mapping[int, tuple[RoleInput, ...]] | None = None,
) -> tuple[NativeRecordGroup, ...]:
    """Compose selected native cells with explicitly declared full row/header paths.

    Paths and note/unit inheritance are upstream structural decisions, not inferred by
    proximity. This adapter reads actual native cell text and source-piece positions;
    incomplete paths remain unresolved. It does not retrieve headers or select tables.
    """
    native = json.loads(context.primary.native_context)
    table = next(
        (
            item
            for item in native["items"]
            if item.get("self_ref", item.get("pointer")) == table_pointer
        ),
        None,
    )
    if table is None or "table_cells" not in table.get("data", {}):
        raise GlinerRefused("selected native table cell structure is unavailable")
    native_cells = table["data"]["table_cells"]
    inherited = inherited or {}
    groups = []

    def reading(role: str, path: tuple[int, ...]) -> RoleInput:
        if not path or len(set(path)) != len(path):
            return RoleInput(
                role,
                state="unresolved",
                inspected_pointer=table_pointer,
                reason="native structural path is missing or ambiguous",
            )
        spans = []
        for index in path:
            if type(index) is not int or not 0 <= index < len(native_cells):
                return RoleInput(
                    role,
                    state="unresolved",
                    inspected_pointer=table_pointer,
                    reason="native structural path references a missing cell",
                )
            cell = native_cells[index]
            located = _item_spans(context, table_pointer, cell_index=index)
            if not located or "".join(piece.text for piece in located) != cell.get("text"):
                return RoleInput(
                    role,
                    state="unresolved",
                    inspected_pointer=table_pointer,
                    reason="complete native cell text is not located in this selected context",
                )
            spans.extend(located)
        return RoleInput(role, spans=tuple(spans))

    for index in cells:
        if type(index) is not int or not 0 <= index < len(native_cells):
            groups.append(
                NativeRecordGroup(
                    (
                        RoleInput(
                            "cell",
                            state="unresolved",
                            inspected_pointer=table_pointer,
                            reason="selected native cell does not exist",
                        ),
                    ),
                    "missing native cell",
                )
            )
            continue
        cell_pointer = f"{table_pointer}/data/table_cells/{index}"
        text = native_cells[index].get("text")
        value = (
            RoleInput(
                "cell_value",
                state="unstated",
                inspected_pointer=cell_pointer,
                reason="native table cell text is explicitly blank",
            )
            if text == ""
            else reading("cell_value", (index,))
        )
        groups.append(
            NativeRecordGroup(
                (
                    RoleInput("table", native_pointer=table_pointer),
                    RoleInput("cell", native_pointer=cell_pointer),
                    reading("row_identity", row_paths.get(index, ())),
                    reading("header_path", header_paths.get(index, ())),
                    value,
                    *inherited.get(index, ()),
                ),
                "explicit native cell, complete row/header paths and declared inheritance",
            )
        )
    return tuple(groups)


def native_formula_group(
    context: NativeSourceContext,
    occurrence: FormulaOccurrence,
    *,
    scope_pointer: str,
    declarations: tuple[RoleInput, ...] = (),
) -> NativeRecordGroup:
    """Reuse a native formula occurrence with independently located declaration roles.

    Only original text reconstructing this canonical source view is supported. Recognized
    LaTeX coordinates, parser symbol ordinals and nearby prose cannot supply formula evidence.
    Symbol declarations are explicitly supplied, never joined by equal spellings.
    """
    if occurrence.conversion_digest != context.primary.native_product.content_digest:
        raise GlinerRefused("formula occurrence belongs to another pinned native product")
    spans = _item_spans(context, occurrence.item_pointer)
    located = bool(spans) and "".join(span.text for span in spans) == occurrence.original_text
    formula = (
        RoleInput("formula", spans=spans)
        if located
        else RoleInput(
            "formula",
            state="unresolved",
            inspected_pointer=occurrence.item_pointer,
            reason="original formula text is not located in this canonical source context",
        )
    )
    return NativeRecordGroup(
        (formula, RoleInput("scope", native_pointer=scope_pointer), *declarations),
        "native formula occurrence plus separately addressed declaration/scope",
        (_digest("native-formula", asdict(occurrence)),),
    )


def reconcile_record_candidates(
    prepared: PreparedRelease, results: Sequence[AssemblyResult]
) -> tuple[BaseModel, ...]:
    """Reconcile equal source readings across windows, retaining all observation dependencies.

    Callers retain the input results/raw reports. Equal text at distinct occurrence positions
    remains distinct; differing qualifications remain coherent candidate alternatives.
    This is a keyed reduction over records, with no candidate Cartesian matching.
    """
    merged: dict[str, dict[str, Any]] = {}
    coordinates = []
    for result in results:
        coordinates.extend(result.coordinate_texts)
        for record in result.records:
            row = record.model_dump(mode="python")
            if row["standing"] != "candidate":
                raise GlinerRefused("window reconciliation consumes private candidates only")
            content = {
                key: value
                for key, value in row.items()
                if key not in {"computation_dependencies", "interpretation_id"}
            }
            key = _digest("source-reading", content)
            if key in merged:
                row["computation_dependencies"] = tuple(
                    sorted(
                        set(row.get("computation_dependencies", ()))
                        | set(merged[key].get("computation_dependencies", ()))
                    )
                )
            row["interpretation_id"] = interpretation_identity(row)
            merged[key] = row
    sources: dict[str, list[dict[str, Any]]] = {}
    for row in merged.values():
        sources.setdefault(row["pin"]["source"], []).append(row)
    return tuple(
        record
        for source, rows in sources.items()
        for record in bind_record_candidates(
            prepared, source=source, records=rows, coordinate_texts=coordinates
        )
    )
