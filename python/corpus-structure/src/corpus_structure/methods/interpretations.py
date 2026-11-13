"""Replay explicit reviewed interpretations through ordinary source-task completion.

This deterministic producer retains authored decisions; it does not infer mappings or
change extracted records. Focus coordinates remain owned by the referenced record.
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from corpus_structure.core.method import (
    Digest,
    MethodContext,
    Resources,
    SourceRunContext,
    UnitRef,
    UnitResult,
    UnitView,
)
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

    def select(
        self, run: SourceRunContext, cfg: AuthoredInterpretationConfig | AuthoredSourceRecordsConfig
    ) -> tuple[UnitRef, ...]:
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

    def input_digest(
        self, unit: UnitView, cfg: AuthoredInterpretationConfig | AuthoredSourceRecordsConfig
    ) -> Digest:
        return Digest(canonical_bytes(cfg.model_dump(mode="json")))


class TerminologyInterpretationMethod(_AuthoredSourceMethod):
    name = "interpret.terminology"
    semantic_type = "terminology.interpretation"
    Config = AuthoredInterpretationConfig

    def run(
        self, units: Sequence[UnitView], cfg: AuthoredInterpretationConfig, ctx: MethodContext
    ) -> tuple[UnitResult, ...]:
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

    def run(
        self, units: Sequence[UnitView], cfg: AuthoredSourceRecordsConfig, ctx: MethodContext
    ) -> tuple[UnitResult, ...]:
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


# Shared family meaning is inherited once; supplying declarations and public
# subclass entrypoints remain separate facts in the effective compiler products.
_AuthoredSourceMethod.__data_operation__ = {
    "abstract": True,
    "profile": "selection",
    "subject": "exact-original-source-view",
    "context": ["project", "source-view", "native-product", "projection", "source-recipe"],
    "entrypoints": ["select", "input_digest", "run"],
    "roles": [
        {
            "name": "authored",
            "kind": "urn:corpus:kind:authored-source-content",
            "direction": "input",
            "minimum": 1,
            "maximum": 1,
            "collection": "scalar",
            "presence": "required",
            "support": {
                "provenance": "exact",
                "identity_requirements": ["episode"],
                "source": "original-source-view",
                "coverage": "all-authored-members",
                "closure": ["native-product", "projection", "source-recipe"],
            },
        },
        {
            "name": "retained",
            "kind": "urn:corpus:kind:authored-source-result",
            "direction": "output",
            "minimum": 1,
            "maximum": None,
            "collection": "sequence",
            "presence": "required",
        },
    ],
    "kinds": [
        {
            "id": "urn:corpus:kind:authored-source-content",
            "primitive": "json",
            "scope": "original-source-view",
            "interpretation": "located-authored-content-v1",
        },
        {
            "id": "urn:corpus:kind:authored-source-result",
            "primitive": "json",
            "scope": "original-source-view",
            "interpretation": "authored-unit-result-v1",
        },
    ],
    "applicability": ["exactly-one-selected-original-view", "authored-record-project-view-match"],
    "invariants": ["retained-authorship", "exact-source-coordinate-custody"],
    "coverage": "all-explicitly-authored-members",
    "outcomes": ["produced", "invalid-source", "invalid-authored-content", "cancelled"],
    "precision": "exact-authored-payload",
    "dependencies": [],
    "effects": [],
    "capabilities": {
        "forms": ["batch"],
        "preparation": "validated-authored-config",
        "cancellation": "member-boundary",
        "ownership": "immutable-selected-source-and-config",
        "limits": ["one-to-one-hundred-authored-members"],
    },
    "behavior": "retain-authored-source-content-v1",
    "parameters": {},
    "binding": {"operator": "scan", "roles": ["authored"]},
    "opaque": [
        {
            "reference": "pydantic",
            "contract": "pydantic2-authored-config-v1",
            "role": "typed-validation",
        },
        {
            "reference": "corpus_structure.core.method",
            "contract": "source-method-typed-ports-v1",
            "role": "typed-input-result",
        },
        {
            "reference": "corpus_structure.core.vocab",
            "contract": "source-method-enumerations-v1",
            "role": "outcome-type",
        },
        {
            "reference": "corpus_structure.semantic.identity.canonical_bytes",
            "contract": "canonical-json-v1",
            "role": "input-value-encoding",
        },
        {
            "reference": "corpus_structure.semantic.structural_products.ExternalSourceRef",
            "contract": "exact-external-source-reference-v1",
            "role": "source-support",
        },
        {
            "reference": "corpus_structure.semantic.contributions.operation_identity",
            "contract": "authored-operation-identity-v1",
            "role": "operation-key",
        },
        {
            "reference": "corpus_structure.semantic.interpretations.interpretation_contribution",
            "contract": "interpretation-contribution-v1",
            "role": "authored-result-validation",
        },
        {
            "reference": "collections.abc.Sequence",
            "contract": "python-3.14-sequence-v1",
            "role": "type-interpretation",
        },
    ],
    "bound_inputs": ["run", "cfg", "ctx"],
}
TerminologyInterpretationMethod.__data_operation__ = {
    "abstract": False,
    "id": "urn:corpus:operation:interpret-terminology",
}
MeasurementInterpretationMethod.__data_operation__ = {
    "abstract": False,
    "id": "urn:corpus:operation:interpret-measurement",
}
AuthorSourceRecordsMethod.__data_operation__ = {
    "abstract": False,
    "id": "urn:corpus:operation:author-source-records",
}
