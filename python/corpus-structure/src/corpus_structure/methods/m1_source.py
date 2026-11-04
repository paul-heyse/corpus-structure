"""One run-owned CPU source candidate producer, before knowledge acceptance."""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
from itertools import pairwise
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from corpus_structure.core.method import CoverageDraft, Digest, Resources, UnitRef, UnitResult
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.ingest.annotations import AnnotationProfile
from corpus_structure.ingest.sentences import SentenceConfig, pipeline
from corpus_structure.methods.gliner import GlinerInput, GlinerProfile, GlinerRefused
from corpus_structure.methods.gliner_worker import GlinerWorker, GlinerWorkerError
from corpus_structure.methods.source_preparation import POLICY, prepare_source
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.source_contexts import (
    ContextRefused,
    NativeSourcePin,
    NativeSpanEvidence,
)

FAMILIES = {
    "definition": ("DefinitionRecordFields", "term"),
    "assertion": ("AssertionRecordFields", "predicate"),
    "measurement": ("MeasurementRecordFields", "original_value"),
    "table": ("TableRecordFields", "cell_value"),
    "formula_context": ("FormulaRecordFields", "formula"),
}


def _retained_report(report, profiles):
    """Retain raw decoder output and reconstructible preparation without passage copies."""
    row = asdict(report)
    preparation = row["preparation"]
    preparation["consumed_text_sha256"] = sha256(
        preparation.pop("consumed_text").encode()
    ).hexdigest()
    effective = row.pop("effective_profile_json")
    identity = sha256(effective.encode()).hexdigest()
    profiles.setdefault(identity, effective)
    row["effective_profile_ref"] = identity
    return row


def _structural_groups(view, selection, context):
    """Only explicit native table geometry and an existing formula occurrence owner."""
    from corpus_structure.methods.math.pdf import FormulaOccurrence
    from corpus_structure.methods.record_assembly import native_formula_group, native_table_groups

    node = next(item for item in view.items if item["self_ref"] == selection.region)
    if selection.families == ("formula_context",):
        health = {row["pointer"]: row["outcome"] for row in view.health.get("formula_outcomes", ())}
        status = health.get(selection.region, "unknown")
        if status not in {"succeeded", "failed", "unknown", "not_requested"}:
            status = "unknown"
        occurrence = FormulaOccurrence(
            view.ref.native_product.content_digest,
            selection.region,
            node.get("text", ""),
            node.get("orig", ""),
            status,
        )
        return (native_formula_group(context, occurrence, scope_pointer=view.ref.section_pointer),)
    if selection.families != ("table",):
        return ()
    cells = node.get("data", {}).get("table_cells", ())
    row_paths, header_paths = {}, {}
    selected = tuple(
        index
        for index, cell in enumerate(cells)
        if not cell.get("column_header") and not cell.get("row_header")
    )

    def extent(cell, axis):
        a, b = cell.get(f"start_{axis}_offset_idx"), cell.get(f"end_{axis}_offset_idx")
        return (a, b) if type(a) is int and type(b) is int and 0 <= a < b else None

    for index in selected:
        target_row, target_col = extent(cells[index], "row"), extent(cells[index], "col")
        if target_row is None or target_col is None:
            continue
        rows, headers = [], []
        for other, cell in enumerate(cells):
            row, col = extent(cell, "row"), extent(cell, "col")
            if row is None or col is None:
                continue
            if (
                cell.get("row_header")
                and row[0] <= target_row[0]
                and row[1] >= target_row[1]
                and col[1] <= target_col[0]
            ):
                rows.append((*col, *row, other))
            if (
                cell.get("column_header")
                and col[0] <= target_col[0]
                and col[1] >= target_col[1]
                and row[1] <= target_row[0]
            ):
                headers.append((*row, *col, other))

        def nested_path(candidates):
            ordered = sorted(candidates)
            # Each level occupies a distinct band. Coverage can stay equal or narrow
            # toward the target; crossing sibling extents cannot form one native path.
            if any(
                parent[1] > child[0] or parent[2] > child[2] or parent[3] < child[3]
                for parent, child in pairwise(ordered)
            ):
                return ()
            return tuple(candidate[4] for candidate in ordered)

        row_paths[index] = nested_path(rows)
        header_paths[index] = nested_path(headers)
    return native_table_groups(
        context,
        table_pointer=selection.region,
        cells=selected,
        row_paths=row_paths,
        header_paths=header_paths,
    )


class M1Config(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    policy: Literal["m1-canonical-related-context-candidates-2"] = POLICY
    source_dependencies: Literal["source_view_product"] = "source_view_product"
    source_dependency_method: Literal["extract.m1_annotations"] = "extract.m1_annotations"
    snapshot: Path
    checkpoint: str
    revision: str
    artifact_hashes: tuple[tuple[str, str], ...]
    threads: int = Field(default=4, ge=1, le=16)
    parent_threads: int = Field(default=1, ge=1, le=16)
    max_context_chars: int = Field(default=2048, ge=1, le=8192)
    max_context_pieces: int = Field(default=64, ge=1, le=256)
    max_annotation_chars: int = Field(default=32768, ge=1)
    sentences: SentenceConfig = Field(default_factory=lambda: SentenceConfig(exclude=("ner",)))
    threshold: float = Field(default=0.5, ge=0, le=1)
    timeout_seconds: float = Field(default=120, gt=0, allow_inf_nan=False)
    pack_descriptions: dict[str, dict[str, str]] = Field(default_factory=dict)

    @field_validator("pack_descriptions")
    @classmethod
    def described_families(cls, value):
        if set(value) - set(FAMILIES):
            raise ValueError("pack descriptions name an unsupported M1 family")
        if any(
            not description.strip() for roles in value.values() for description in roles.values()
        ):
            raise ValueError("pack role descriptions must be nonempty")
        return value

    def profile(self) -> GlinerProfile:
        return GlinerProfile(
            self.snapshot,
            self.checkpoint,
            self.revision,
            self.artifact_hashes,
            threads=self.threads,
            timeout_seconds=self.timeout_seconds,
        )


def configured_packs(prepared, cfg):
    """Release-owned roles plus explicit extraction instructions, prepared once per source."""
    from corpus_structure.methods.record_packs import family_pack

    return {
        family: family_pack(
            prepared,
            contract=contract,
            anchor_role=anchor,
            descriptions=cfg.pack_descriptions.get(family),
        )
        for family, (contract, anchor) in FAMILIES.items()
    }


class M1Candidates:
    name = "extract.m1_candidates"
    version = "2"
    family = MethodFamily.EXTRACT
    unit_type = TaskUnitType.SOURCE_VIEW
    tier = MethodTier.ENCODER
    confidence_source = None
    Config = M1Config
    resources = Resources(worker="cpu", batch_size=1, max_concurrency=1)

    def __init__(self) -> None:
        self._worker: GlinerWorker | None = None

    def close(self) -> None:
        if self._worker is not None:
            self._worker.close()
        self._worker = None

    def select(self, run, cfg):
        return tuple(
            UnitRef(TaskUnitType.SOURCE_VIEW, view.id, view.key)
            for view in run.reader.source_views()
            if view.analysis_eligible
        )

    def input_digest(self, unit, cfg):
        if unit.ref.unit_id is None:
            raise ValueError("M1 requires a selected source view")
        view = unit.run.reader.source_view(unit.ref.unit_id)
        from corpus_structure.methods.m1_annotations import consume_annotations

        _, _, annotation_result = consume_annotations(
            unit.run.reader, view, AnnotationProfile(cfg.sentences)
        )
        return Digest(
            canonical_bytes(
                dict(
                    policy=cfg.policy,
                    native=view.ref.native_product.values(),
                    projection=view.ref.projection_digest,
                    recipe=view.ref.recipe_digest,
                    annotation_product=sha256(canonical_bytes(annotation_result)).hexdigest(),
                    context_membership=unit.run.reader.source_context_membership(view.ref.id),
                )
            )
        )

    def _resident(self, profile):
        if self._worker is None:
            self._worker = GlinerWorker(profile)
        elif self._worker.profile.fingerprint != profile.fingerprint:
            raise GlinerRefused("one M1 run cannot switch resident profiles")
        return self._worker

    def run(self, units, cfg, ctx):
        return tuple(self._source(unit, cfg, ctx) for unit in units)

    def _source(self, unit, cfg, ctx):
        from threadpoolctl import ThreadpoolController

        from corpus_structure.methods.record_assembly import (
            NativeRecordGroup,
            RoleInput,
            assemble_native_records,
            assemble_records,
            reconcile_record_candidates,
        )

        if unit.ref.unit_id is None:
            raise ValueError("M1 requires a selected source view")
        ctx.check_active()
        packs = configured_packs(ctx.reader.prepared, cfg)
        view = ctx.reader.source_view(unit.ref.unit_id)
        profile = AnnotationProfile(cfg.sentences)
        from corpus_structure.methods.m1_annotations import consume_annotations

        annotations, annotation_errors, annotation_result = consume_annotations(
            ctx.reader, view, profile
        )
        # Load spaCy/native libraries before discovering their thread controllers.
        pipeline(cfg.sentences)
        controller = ThreadpoolController()
        with controller.limit(limits=cfg.parent_threads):
            prepared_source = prepare_source(
                view,
                profile=profile,
                max_chars=cfg.max_context_chars,
                max_pieces=cfg.max_context_pieces,
                max_annotation_chars=cfg.max_annotation_chars,
                check_active=ctx.check_active,
                reader=ctx.reader,
                persisted_annotations=annotations,
                annotation_errors=annotation_errors,
            )
        details: dict[str, Any] = dict(
            policy=cfg.policy,
            standing="private_uncalibrated_candidates",
            source_pin=asdict(NativeSourcePin.from_source(prepared_source.source)),
            regions=[asdict(region) for region in prepared_source.regions],
            contexts=[asdict(selection) for selection in prepared_source.selections],
            annotation_product=dict(
                method=annotation_result["method"],
                input_hash=annotation_result["input_hash"],
                configuration_hash=annotation_result["configuration_hash"],
                dependency_digest=sha256(canonical_bytes(annotation_result)).hexdigest(),
                blocks=[product.dependency_digest for product in prepared_source.annotations],
            ),
            annotation_errors=list(prepared_source.annotation_errors),
            exclusions=list(prepared_source.exclusions),
            effective_profiles={},
            reports=[],
            runtime=dict(
                parent_threads=cfg.parent_threads,
                child_threads=cfg.threads,
                concurrent_sources=1,
                aggregate_rss="unqualified",
                ordinary_workload="unqualified",
            ),
        )
        assemblies = []
        coverage = []
        details["execution"] = [
            dict(context=index, family=family, outcome="pending", reason="not yet executed")
            for index, selection in enumerate(prepared_source.selections)
            for family in selection.families
        ]
        execution = {(row["context"], row["family"]): row for row in details["execution"]}
        for region in prepared_source.regions:
            for family in region.families:
                coverage.append(
                    CoverageDraft(
                        family="routing/" + family,
                        scope=region.pointer,
                        outcome="complete"
                        if region.outcome in {"selected", "empty"}
                        else "unsupported"
                        if region.outcome == "unsupported"
                        else "partial",
                        reason=region.reason,
                    )
                )
        if prepared_source.annotation_errors:
            reason = "; ".join(prepared_source.annotation_errors)
            for row in details["execution"]:
                row.update(outcome="not_run", reason="required annotation profile unavailable")
            return UnitResult(
                ref=unit.ref,
                outcome=ObservationOutcome.FAILED,
                error=reason,
                parse_detail=details,
                coverage=tuple(coverage),
            )
        for index, selection in enumerate(prepared_source.selections):
            ctx.check_active()
            context = selection.context(
                prepared_source.source,
                max_chars=cfg.max_context_chars,
                max_pieces=cfg.max_context_pieces,
                related=prepared_source.related,
                preparation=prepared_source.preparation,
            )
            for family in selection.families:
                contract, anchor = FAMILIES[family]
                try:
                    native_groups = (
                        _structural_groups(view, selection, context)
                        if family in {"table", "formula_context"}
                        else ()
                    )
                    occurrence_roles = ("cell",) if family == "table" else (anchor,)
                    native_diagnostics = ()
                    native_records = ()
                    if native_groups:
                        native = assemble_native_records(
                            ctx.reader.prepared,
                            context,
                            contract=contract,
                            occurrence_roles=occurrence_roles,
                            policy_version=cfg.policy,
                            groups=native_groups,
                        )
                        assemblies.append(native)
                        native_diagnostics = native.diagnostics
                        native_records = native.records
                        details["reports"].append(
                            dict(
                                context=index,
                                family=family,
                                operation="native_structure",
                                groups=[asdict(group) for group in native_groups],
                                diagnostics=[asdict(d) for d in native.diagnostics],
                            )
                        )
                    pack = packs[family]
                    (report,) = self._resident(cfg.profile()).extract(
                        pack,
                        (GlinerInput.from_context(context),),
                        threshold=cfg.threshold,
                        check_active=ctx.check_active,
                    )
                    report_entry = dict(
                        context=index,
                        family=family,
                        report=_retained_report(report, details["effective_profiles"]),
                        diagnostics=[],
                        association_diagnostics=[],
                    )
                    details["reports"].append(report_entry)
                    supplements = {}
                    for group_index, group in enumerate(report.raw.get(family, ())):
                        if family == "definition":
                            supplements[group_index] = NativeRecordGroup(
                                (RoleInput("scope", native_pointer=view.ref.section_pointer),),
                                "selected native section is the explicit definition scope",
                            )
                        elif family == "formula_context" and native_groups:
                            supplements[group_index] = native_groups[0]
                        elif family == "table":
                            raw_value = group.get("cell_value")
                            if isinstance(raw_value, dict):
                                try:
                                    evidence = context.map_span(
                                        raw_value["start"],
                                        raw_value["end"],
                                        literal=raw_value["text"],
                                        allow_multiple=True,
                                    )
                                except (KeyError, TypeError, ContextRefused) as error:
                                    report_entry["association_diagnostics"].append(
                                        dict(group=group_index, reason=str(error))
                                    )
                                    continue
                                indices = set()
                                for piece in evidence:
                                    if not isinstance(piece, NativeSpanEvidence):
                                        raise ContextRefused(
                                            "M1 table association requires native evidence"
                                        )
                                    indices.add(piece.cell_index)
                                if len(indices) == 1 and None not in indices:
                                    cell = next(iter(indices))
                                    pointer = f"{selection.region}/data/table_cells/{cell}"
                                    matching = [
                                        g
                                        for g in native_groups
                                        if any(
                                            f.role == "cell" and f.native_pointer == pointer
                                            for f in g.fields
                                        )
                                    ]
                                    if len(matching) == 1:
                                        supplements[group_index] = matching[0]
                    assembled = assemble_records(
                        ctx.reader.prepared,
                        context,
                        pack,
                        report,
                        contract=contract,
                        anchor_role=anchor,
                        policy_version=cfg.policy,
                        occurrence_roles=occurrence_roles,
                        supplements=supplements,
                    )
                    assemblies.append(assembled)
                    report_entry["diagnostics"] = [asdict(d) for d in assembled.diagnostics]
                    incomplete = bool(assembled.diagnostics or native_diagnostics)
                    coverage.append(
                        CoverageDraft(
                            family=family,
                            scope=f"{selection.region}:{selection.start}:{selection.end}",
                            outcome="partial" if incomplete else "complete",
                            reason="assembly diagnostics retained"
                            if incomplete
                            else (
                                "extraction complete; empty output leaves source meaning unresolved"
                            ),
                        )
                    )
                    execution[index, family].update(
                        outcome="partial" if incomplete else "complete",
                        reason="candidate output"
                        if assembled.records or native_records
                        else "no located candidate output",
                    )
                except GlinerRefused as error:
                    execution[index, family].update(outcome="limited", reason=str(error))
                    details["reports"].append(
                        dict(context=index, family=family, outcome="limited", reason=str(error))
                    )
                    coverage.append(
                        CoverageDraft(
                            family=family,
                            scope=f"{selection.region}:{selection.start}:{selection.end}",
                            outcome="partial",
                            reason=str(error),
                        )
                    )
                except GlinerWorkerError as error:
                    execution[index, family].update(outcome="failed", reason=str(error))
                    for row in details["execution"]:
                        if row["outcome"] == "pending":
                            row.update(
                                outcome="not_run",
                                reason="resident worker failed; no automatic restart/fallback",
                            )
                    details["reports"].append(
                        dict(context=index, family=family, outcome="failed", reason=str(error))
                    )
                    return UnitResult(
                        ref=unit.ref,
                        outcome=ObservationOutcome.FAILED,
                        error=str(error),
                        parse_detail=details,
                        coverage=(
                            *coverage,
                            CoverageDraft(
                                family=family,
                                scope=selection.region,
                                outcome="failed",
                                reason=str(error),
                            ),
                        ),
                    )
        ctx.check_active()
        records = tuple(
            record.model_dump(mode="python")
            for record in reconcile_record_candidates(ctx.reader.prepared, assemblies)
        )
        return UnitResult(
            ref=unit.ref,
            outcome=ObservationOutcome.PRODUCED if records else ObservationOutcome.EMPTY,
            records=records,
            coverage=tuple(coverage),
            parse_detail=details,
        )
