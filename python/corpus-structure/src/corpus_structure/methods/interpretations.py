"""Replay explicit reviewed interpretations through ordinary source-task completion.

This deterministic producer retains authored decisions; it does not infer mappings or
change extracted records. Focus coordinates remain owned by the referenced record.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from corpus_structure.core.method import Digest, Resources, UnitRef, UnitResult
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_products import ExternalSourceRef


class AuthoredInterpretationConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source: ExternalSourceRef
    reviews: tuple[dict[str, JsonValue], ...] = Field(min_length=1, max_length=100)


class _AuthoredSourceMethod:
    version = "1"
    family = MethodFamily.RESOLVE
    tier = MethodTier.DETERMINISTIC
    unit_type = TaskUnitType.SOURCE_VIEW
    confidence_source = None
    resources = Resources()

    def select(self, run, cfg):
        selected = [
            view
            for view in run.reader.source_views()
            if view.id == cfg.source.source_view_id
            and view.native_product.content_digest == cfg.source.native_content_digest
            and view.projection_digest == cfg.source.projection_digest
            and view.recipe_digest == cfg.source.recipe_digest
        ]
        if len(selected) != 1:
            raise ValueError(
                "authored interpretations require their exact selected original source view"
            )
        return (UnitRef(TaskUnitType.SOURCE_VIEW, selected[0].id, selected[0].key),)

    def input_digest(self, unit, cfg):
        return Digest(canonical_bytes(cfg.model_dump(mode="json")))


class TerminologyInterpretationMethod(_AuthoredSourceMethod):
    name = "interpret.terminology"
    semantic_type = "terminology.interpretation"
    Config = AuthoredInterpretationConfig

    def run(self, units, cfg, ctx):
        from corpus_structure.semantic.contributions import operation_identity
        from corpus_structure.semantic.interpretations import interpretation_contribution

        outputs = []
        for unit in units:
            ctx.check_active()
            source = cfg.source
            pin = dict(
                source=unit.ref.unit_key,
                native_product_task_id=source.native_task_id,
                product_key=source.native_product_key,
                product_digest=source.native_content_digest,
                projection_digest=source.projection_digest,
                recipe_digest=source.recipe_digest,
                source_view_id=source.source_view_id,
            )
            operation = operation_identity(
                self.name, self.version, cfg.model_dump(mode="json"), pin
            )
            rows = []
            for i, review in enumerate(cfg.reviews):
                ctx.check_active()
                reference = review.get("source_record")
                # Original coordinate custody may predate this retained record result.
                # Native completion authenticates the result, field and full source pins.
                if not isinstance(reference, dict) or any(
                    reference.get(key) != value
                    for key, value in dict(
                        project_id=source.project_id,
                        source_view_id=source.source_view_id,
                    ).items()
                ):
                    raise ValueError(
                        "authored record target differs from original source project/view"
                    )
                rows.append(
                    interpretation_contribution(
                        ctx.reader.prepared,
                        semantic_type=self.semantic_type,
                        payload=review,
                        operation_key=operation,
                        item_key=str(i),
                        pin=pin,
                        anchors=(),
                    )
                )
            outputs.append(
                UnitResult(
                    ref=unit.ref,
                    outcome=ObservationOutcome.PRODUCED,
                    contributions=tuple(rows),
                    contribution_operations=(
                        dict(
                            operation_key=operation,
                            question=self.name,
                            operation_version=self.version,
                            outcome="succeeded",
                            inspected_count=len(cfg.reviews),
                            emitted_count=len(rows),
                        ),
                    ),
                )
            )
        return tuple(outputs)


class MeasurementInterpretationMethod(TerminologyInterpretationMethod):
    name = "interpret.measurement"
    semantic_type = "measurement.interpretation"


class AuthoredSourceRecordsConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source: ExternalSourceRef
    records: tuple[dict[str, JsonValue], ...] = Field(min_length=1, max_length=100)


class AuthorSourceRecordsMethod(_AuthoredSourceMethod):
    """Retain explicitly authored, located records; complete existing schemas normally."""

    name = "interpret.source_records"
    family = MethodFamily.EXTRACT
    Config = AuthoredSourceRecordsConfig

    def run(self, units, cfg, ctx):
        outputs = []
        for unit in units:
            ctx.check_active()
            records = tuple(
                ctx.reader.prepared.validate_json(
                    "SourceRecord", canonical_bytes(record)
                ).model_dump(mode="python", exclude_none=True)
                for record in cfg.records
            )
            for record in records:
                pin = record.get("pin")
                if (
                    not isinstance(pin, dict)
                    or pin.get("source_view_id") != unit.ref.unit_id
                    or pin.get("product_digest") != cfg.source.native_content_digest
                    or pin.get("projection_digest") != cfg.source.projection_digest
                ):
                    raise ValueError("authored record differs from selected source")
            outputs.append(
                UnitResult(ref=unit.ref, outcome=ObservationOutcome.PRODUCED, records=records)
            )
        return tuple(outputs)
