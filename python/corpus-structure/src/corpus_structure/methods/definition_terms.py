"""Project retained definition-term roles into authenticated source occurrences.

This is a location/role projection of a retained component, not fresh discovery,
independent semantic support, or a supplied mention interface.
"""

from pydantic import ConfigDict, Field, model_validator

from corpus_structure.semantic.contributions import (
    contribution_identity,
    occurrence_identity,
    operation_identity,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.source_contexts import (
    NativeSourceContext,
    SourceSlice,
    evidence_anchor,
    record_source_pin,
)
from corpus_structure.semantic.structural_products import (
    ExternalSourceRef,
    RetainedComponentRef,
    RetainedDefinitionRoleRef,
    StructuralValue,
)


class DefinitionTermsConfig(StructuralValue):
    model_config = ConfigDict(frozen=True, extra="forbid")
    component_refs: tuple[RetainedComponentRef, ...] = Field(default=(), max_length=256)
    role_refs: tuple[RetainedDefinitionRoleRef, ...] = Field(default=(), max_length=256)
    source_product_digest: str = Field(pattern="^[0-9a-f]{64}$")
    source_projection_digest: str = Field(pattern="^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def distinct_components(self):
        refs = (*self.component_refs, *self.role_refs)
        if not refs or (self.component_refs and self.role_refs):
            raise ValueError("select one retained definition reference kind")
        if len(set(refs)) != len(refs):
            raise ValueError("definition role projection contains duplicate references")
        return self


def project_retained_definition_terms(reader, view, cfg, *, check_active=lambda: None):
    """Locate exact original definition roles; the caller supplies the retained source."""
    if (view.ref.native_product.content_digest != cfg.source_product_digest
        or view.ref.projection_digest != cfg.source_projection_digest):
        raise ValueError("definition term projection differs from configured original source")
    check_active()
    frame = native_source_frame(view, ())
    pin = record_source_pin(frame)
    context = NativeSourceContext(
        frame,
        (),
        (SourceSlice(view.ref.id, 0, len(frame.text)),),
        "retained definition role projection",
        "retained-definition-role-2",
        "whole selected source",
        max_chars=len(frame.text),
        max_pieces=max(1, len(view.pieces)),
    )
    operation_key = operation_identity(
        "locate.definition_terms", "2", cfg.model_dump(mode="json"), pin
    )
    products, coordinates = [], {}
    dependencies = []
    for reference in (*cfg.component_refs, *cfg.role_refs):
        check_active()
        if isinstance(reference, RetainedDefinitionRoleRef):
            report = reader.retained_structural_report(reference.report)["report"]
            (candidate,) = [
                row
                for row in report["definition_components"]["role_candidates"]
                if (row["role"], row["envelope"], row["index"])
                == (reference.role, reference.envelope, reference.index)
            ]
            span = candidate["span"]
            semantic_type = (
                "definition.term"
                if reference.role == "term"
                else "definition.defining_text"
            )
            item_key = "retained-definition-role:" + reference.identity
            deps = (reference.report.product_id, reference.envelope, item_key)
            meaning = dict(
                role=reference.role, role_reference=reference.model_dump(mode="json")
            )
            kind = "proposal"
        else:
            retained = reader.retained_definition_component(reference)
            report, span = retained["report"], retained["component"]["term"]
            semantic_type = "definition.term"
            item_key = "retained-component:" + reference.identity
            deps = (reference.product_id, reference.component_id, item_key)
            meaning = dict(
                role="defined_term", component_reference=reference.model_dump(mode="json")
            )
            kind = "occurrence"
        passage = next(
            p for p in report["inputs"]["passages"] if p["passage_id"] == span["passage_id"]
        )
        source = next(
            s
            for s in report["inputs"]["sources"]
            if ExternalSourceRef.model_validate(s).identity == passage["source_ref"]
        )
        expected = dict(
            source_view_id=view.ref.id,
            native_task_id=view.ref.native_product.task_id,
            native_product_key=view.ref.native_product.product_key,
            native_content_digest=view.ref.native_product.content_digest,
            projection_digest=view.ref.projection_digest,
            recipe_digest=view.ref.recipe_digest,
        )
        if any(source.get(key) != value for key, value in expected.items()):
            raise ValueError("retained definition term belongs to another original source")
        anchors, located_coordinates = locate_definition_span(context, span)
        for coordinate in located_coordinates:
            coordinates[canonical_bytes({key: value for key, value in coordinate.items() if key != "text"})] = coordinate
        dependencies.extend(deps)
        row = dict(
            contract="RetainedContributionSemantics",
            kind=kind,
            semantic_type=semantic_type,
            operation_key=operation_key,
            item_key=item_key,
            pin=pin,
            anchors=tuple(anchors),
            occurrence_id=occurrence_identity(anchors),
            disposition="located_proposal",
            standing="retained_private",
            score_state="missing",
            computation_dependencies=deps,
            value=source_value(meaning),
        )
        row["contribution_id"] = contribution_identity(row)
        products.append(row)
    operation = dict(
        operation_key=operation_key,
        question="locate_role_from_retained_definition_evidence",
        operation_version="2",
        outcome="succeeded",
        inspected_count=len(cfg.component_refs) + len(cfg.role_refs),
        emitted_count=len(products),
        computation_dependencies=tuple(dict.fromkeys(dependencies)),
    )
    return tuple(products), (operation,), tuple(coordinates.values())


def locate_definition_span(context, span, *, offset=0):
    """Map one retained half-open literal span through its actual source owner."""
    anchors, coordinates = [], []
    for piece in context.map_span(span["start"] - offset, span["end"] - offset, literal=span["text"], allow_multiple=True):
        anchor, coordinate = evidence_anchor(context, piece, native=True)
        anchors.append(anchor)
        coordinates.append(coordinate)
    return tuple(anchors), tuple(coordinates)
