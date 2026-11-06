"""Project retained definition-term roles into authenticated source occurrences.

This is a location/role projection of a retained component, not fresh discovery,
independent semantic support, or a supplied mention interface.
"""

from pydantic import ConfigDict, Field, model_validator

from corpus_structure.core.method import Digest, Resources, UnitRef, UnitResult
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.semantic.contributions import contribution_identity, occurrence_identity, operation_identity
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.source_contexts import NativeSourceContext, SourceSlice, evidence_anchor, record_source_pin
from corpus_structure.semantic.structural_products import RetainedComponentRef, StructuralValue


class DefinitionTermsConfig(StructuralValue):
    model_config = ConfigDict(frozen=True, extra="forbid")
    component_refs: tuple[RetainedComponentRef, ...] = Field(min_length=1, max_length=256)
    source_product_digest: str = Field(pattern="^[0-9a-f]{64}$")
    source_projection_digest: str = Field(pattern="^[0-9a-f]{64}$")


    @model_validator(mode="after")
    def distinct_components(self):
        if len({reference.identity for reference in self.component_refs}) != len(self.component_refs):
            raise ValueError("definition term projection contains duplicate component references")
        return self


class DefinitionTermsMethod:
    name = "locate.definition_terms"
    version = "1"
    family = MethodFamily.RESOLVE
    tier = MethodTier.DETERMINISTIC
    unit_type = TaskUnitType.SOURCE_VIEW
    confidence_source = None
    Config = DefinitionTermsConfig
    resources = Resources()

    def select(self, run, cfg):
        selected = tuple(UnitRef(TaskUnitType.SOURCE_VIEW, view.id, view.key)
            for view in run.reader.source_views()
            if view.native_product.content_digest == cfg.source_product_digest
            and view.projection_digest == cfg.source_projection_digest)
        if len(selected) != 1:
            raise ValueError("definition term projection needs exactly one authenticated source view")
        return selected

    def input_digest(self, unit, cfg):
        return Digest(canonical_bytes(cfg.model_dump(mode="json")))

    def run(self, units, cfg, ctx):
        results = []
        for unit in units:
            ctx.check_active()
            view = ctx.reader.source_view(unit.ref.unit_id)
            frame = native_source_frame(view, ())
            pin = record_source_pin(frame)
            context = NativeSourceContext(frame, (), (SourceSlice(view.ref.id, 0, len(frame.text)),),
                "retained component term projection", "retained-definition-term-1", "whole selected source",
                max_chars=len(frame.text), max_pieces=max(1, len(view.pieces)))
            operation_key = operation_identity(self.name, self.version, cfg.model_dump(mode="json"), pin)
            products, coordinates = [], {}
            dependencies = []
            for reference in cfg.component_refs:
                ctx.check_active()
                retained = ctx.reader.retained_definition_component(reference)
                component, report = retained["component"], retained["report"]
                term = component["term"]
                passage = next(p for p in report["inputs"]["passages"] if p["passage_id"] == term["passage_id"])
                from corpus_structure.semantic.structural_products import ExternalSourceRef
                source = next(s for s in report["inputs"]["sources"]
                              if ExternalSourceRef.model_validate(s).identity == passage["source_ref"])
                expected = dict(source_view_id=view.ref.id, native_task_id=view.ref.native_product.task_id,
                    native_product_key=view.ref.native_product.product_key,
                    native_content_digest=view.ref.native_product.content_digest,
                    projection_digest=view.ref.projection_digest, recipe_digest=view.ref.recipe_digest)
                if any(source.get(key) != value for key, value in expected.items()):
                    raise ValueError("retained definition term belongs to another original source")
                anchors = []
                for piece in context.map_span(term["start"], term["end"], literal=term["text"], allow_multiple=True):
                    anchor, coordinate = evidence_anchor(context, piece, native=True)
                    anchors.append(anchor)
                    coordinates[canonical_bytes({k: v for k, v in coordinate.items() if k != "text"})] = coordinate
                deps = (reference.product_id, reference.component_id, "retained-component:" + reference.identity)
                dependencies.extend(deps)
                row = dict(contract="RetainedContributionSemantics", kind="occurrence",
                    semantic_type="definition.term", operation_key=operation_key,
                    item_key="retained-component:" + reference.identity, pin=pin, anchors=tuple(anchors),
                    occurrence_id=occurrence_identity(anchors), disposition="located_proposal",
                    standing="retained_private", score_state="missing", computation_dependencies=deps,
                    value=source_value(dict(role="defined_term", component_reference=reference.model_dump(mode="json"))))
                row["contribution_id"] = contribution_identity(row)
                products.append(row)
            operation = dict(operation_key=operation_key, question="locate_term_from_retained_definition_component",
                operation_version=self.version, outcome="succeeded", inspected_count=len(cfg.component_refs),
                emitted_count=len(products), computation_dependencies=tuple(dict.fromkeys(dependencies)))
            results.append(UnitResult(ref=unit.ref, outcome=ObservationOutcome.PRODUCED,
                contributions=tuple(products), contribution_operations=(operation,),
                contribution_coordinate_texts=tuple(coordinates.values())))
        return tuple(results)
