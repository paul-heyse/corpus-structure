"""Actual rich CPU/native publication over explicit original and authored inputs."""

from dataclasses import dataclass, replace
from typing import Any

import pytest
from evaluate.declared_record_native_support import (
    PROJECT,
    ROOT,
    authored,
    project_context,
    request,
)
from evaluate.declared_rich_native_support import NAMESPACE, rich_policy_recipe

from corpus_structure.semantic.data_operation_identity import canonical_identity
from corpus_structure.semantic.rich_knowledge_contracts import (
    DdoRichAdmission,
    DdoRichAuthoredBody,
    DdoRichAuthoredPacket,
    DdoRichAuthoredProposition,
    DdoRichAuthoredPropositions,
    DdoRichConsolidation,
    DdoRichContext,
    DdoRichEntity,
)
from semantic.data_operation_kernel_support import CapturedKernelInputs

DOMAIN = "urn:record-publication:"


def publication_recipe(directory):
    from corpus_structure.semantic.types import SourceArtifact, SourceBundle

    recipe = rich_policy_recipe(directory)
    captured = recipe.captured_inputs
    assert captured is not None
    source = SourceArtifact(
        "record-publication-domain",
        (
            """id: urn:record-publication
name: record_publication
imports: [SOURCE_ROOT]
prefixes: {pub: 'urn:record-publication:'}
default_prefix: pub
classes:
  PublicationSubject:
    is_a: Entity
    annotations: {cs:scope: global}
    attributes:
      value:
        range: Value
        inlined: true
        multivalued: true
        annotations: {cs:constraint_scope: accepted_value, cs:role: predicate, cs:functional: true}
""".replace("SOURCE_ROOT", captured.bundle.root)
        ).encode(),
    )
    return replace(
        recipe,
        name="current-rich-publication",
        captured_inputs=CapturedKernelInputs(
            SourceBundle(source.name, (*captured.bundle.sources, source)),
            captured.dependencies,
            captured.profile,
        ),
    )


@pytest.fixture
def rich_publication(scenario_seeds):
    from evaluate.declared_record_native_support import (
        RecordPublicationCapture,
        table_source_content,
    )

    with scenario_seeds.commit_clone(RecordPublicationCapture(table_source_content())) as clone:
        yield clone.stage.acquired(clone)


def authored_propositions(prepared, model, context, values, *, qualifications=None, entities=None):
    """Author domain propositions without invented computation or source evidence."""
    from corpus_structure.semantic.rich_fact_graph import RichFactGraph

    entities = tuple("authored:subject" for _ in values) if entities is None else entities
    kinds = {item.owner: item.key for item in model.identities if item.domain == "kind"}
    graph = RichFactGraph(
        prepared,
        model,
        context=context,
        entities={
            identifier: frozenset({DOMAIN + "PublicationSubject"}) for identifier in entities
        },
        known_fact_ids=frozenset(),
    )
    bodies: dict[str, DdoRichAuthoredBody] = {}
    for identifier in sorted(set(entities)):
        bodies[identifier] = DdoRichEntity(
            member_type="entity",
            entity_id=identifier,
            class_contracts=(kinds[DOMAIN + "PublicationSubject"],),
            identities=(
                dict(
                    class_contract=kinds[DOMAIN + "PublicationSubject"],
                    fields=(),
                    source_context=None,
                    label="same authored label",
                ),
            ),
            source_members=(),
        )
    for ordinal, value in enumerate(values):
        result = graph.add_property_fact(
            subject_entity=entities[ordinal],
            class_name="PublicationSubject",
            property_name="value",
            value=value,
            qualification=(
                qualifications[ordinal]
                if qualifications is not None
                else {"modality": "asserted", "polarity": True}
            ),
            qualification_class="StatisticsQualification",
        )
        bodies[result.fact.fact_id] = result.fact
        identifier = canonical_identity(
            "rich-authored-proposition",
            [context.identity_record, result.fact.fact_id, result.observed_qualification_value, []],
        ).key
        bodies[identifier] = DdoRichAuthoredProposition(
            member_type="authored-proposition",
            proposition_id=identifier,
            fact_id=result.fact.fact_id,
            observed_qualification_value=result.observed_qualification_value,
            dependencies=(),
        )
    bodies.update((value.value_id, value) for value in graph.values)
    return DdoRichAuthoredPropositions(
        version="rich-authored-propositions-1",
        standing="authored-propositions",
        macros={},
        members=tuple(
            DdoRichAuthoredPacket(
                member_id=identifier,
                kind_contract=kinds[NAMESPACE + type(body).__name__],
                context=DdoRichContext(
                    subject=context.subject,
                    subject_definition=context.subject_definition,
                    original_source=None,
                    analyzed_scope={},
                ),
                body=body,
            )
            for identifier, body in sorted(bodies.items())
        ),
    )


@dataclass(frozen=True)
class RichPublication:
    journey: Any
    demand_id: str
    product: dict[str, Any]
    admission: DdoRichAdmission
    consolidation_product: dict[str, Any]
    consolidation: DdoRichConsolidation
    cut: Any
    uses: tuple
    episodes: tuple


def publish_authored(journey, values, *, inference, qualifications=None, entities=None):
    from corpus_structure.semantic.data_operation_identity import (
        body_identity,
        contextual_product_identity,
    )
    from corpus_structure.semantic.data_operation_json import json_loads
    from corpus_structure.semantic.data_operation_service import execute_data_demand
    from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet, SourceSetEntry
    from corpus_structure.semantic.data_product_reference import DataProductReference
    from corpus_structure.semantic.rich_policy_binding import rich_policy_value
    from corpus_structure.serve.interpretation_authoring import author_interpretations

    context = project_context(journey, "rich.consolidate")
    propositions = authored_propositions(
        journey.kernel.prepared,
        journey.kernel.model,
        context,
        values,
        qualifications=qualifications,
        entities=entities,
    )
    value = propositions.model_dump(mode="python")
    kind = journey.kernel.identities[NAMESPACE + "DdoRichAuthoredPropositions", "kind"]
    product = contextual_product_identity(
        kind=kind, context=context, body=body_identity(value).key
    ).key
    originals = (
        authored(
            journey,
            inference + ":propositions",
            value,
            kind=NAMESPACE + "DdoRichAuthoredPropositions",
            context=context,
        ),
        authored(
            journey,
            inference + ":policy",
            rich_policy_value(journey.kernel.prepared, journey.kernel.model).model_dump(
                mode="python"
            ),
            kind=NAMESPACE + "DdoRichConsolidationPolicy",
            context=context,
        ),
    )
    pending = request(
        journey,
        ("rich.consolidate", "rich.admit"),
        (context,),
        originals=originals,
        source_sets=(
            FrozenSourceSet.unqualified(
                "rich-authored-propositions",
                (
                    SourceSetEntry.from_semantic_source(
                        DataProductReference(product), context=context
                    ),
                ),
            ),
            *tuple(
                FrozenSourceSet.from_selected(name, ())
                for name in (
                    "rich-proposals",
                    "rich-proposal-contexts",
                    "rich-known-universe",
                    "rich-records",
                    "rich-readings",
                    "rich-policy-authorizations",
                )
            ),
        ),
        inference=inference,
    )
    retained = author_interpretations(
        journey.kernel.purpose("write"), journey.kernel.prepared, request=pending
    )
    assert product in {item["product_id"] for item in retained["authored_admissions"]}
    result = execute_data_demand(
        journey.kernel.purpose("write"),
        retained["demand_id"],
        source_root=ROOT,
        admission_engine=journey.kernel.purpose("admit"),
        project_id=PROJECT,
        database_capacity=6,
    )
    frontier = json_loads(result.snapshot)
    assert result.receipt_count == 2, (
        result.receipt_count,
        [(item["operation_id"], item["fate"]) for item in frontier["obligations"]],
    )
    cut, products, uses, episodes, _ = journey.selected_products(
        journey.kernel.purpose("read"),
        retained["demand_id"],
        kind=(NAMESPACE + "DdoRichAdmission", NAMESPACE + "DdoRichConsolidation"),
    )
    kinds = {
        item.owner: item.key for item in journey.kernel.model.identities if item.domain == "kind"
    }
    ((product, admission),) = [
        item
        for item in products
        if item[0]["kind_contract"] == kinds[NAMESPACE + "DdoRichAdmission"]
    ]
    ((private, consolidation),) = [
        item
        for item in products
        if item[0]["kind_contract"] == kinds[NAMESPACE + "DdoRichConsolidation"]
    ]
    return RichPublication(
        journey,
        retained["demand_id"],
        product,
        DdoRichAdmission.model_validate(admission),
        private,
        DdoRichConsolidation.model_validate(consolidation),
        cut,
        uses,
        episodes,
    )


def query_publication(publication, query, **options):
    from corpus_structure.serve.rich_queries import RichQueryRequest, serve_rich_query

    with publication.journey.kernel.purpose("read").begin() as connection:
        return serve_rich_query(
            connection,
            RichQueryRequest(
                project_id=PROJECT,
                demand_id=publication.demand_id,
                product_id=publication.product["id"],
                query=query,
                **options,
            ),
        )


def publish_readings(
    journey,
    readings,
    *,
    source,
    inference,
    authorization=None,
    include_resolution=True,
    page_rows=100,
    max_bytes=8 * 1024**2,
):
    """Consume actual raw/resolved computations; a missing policy grants no reading standing."""
    from evaluate.declared_rich_native_support import selected_entry

    from corpus_structure.semantic.data_operation_service import execute_data_demand
    from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet
    from corpus_structure.semantic.rich_policy_binding import rich_policy_value
    from corpus_structure.serve.interpretation_authoring import author_interpretations

    context = project_context(journey, "rich.consolidate")
    raw = tuple(
        row for row, body in readings.raw if body["source_pin"]["source"] == source.pin.source
    )
    resolved = tuple(
        row for row, body in readings.resolved if body["source_pin"]["source"] == source.pin.source
    )
    assert len(raw) == len(resolved) == 1
    pending = request(
        journey,
        ("rich.consolidate", "rich.admit"),
        (context,),
        originals=(
            authored(
                journey,
                inference + ":policy",
                rich_policy_value(journey.kernel.prepared, journey.kernel.model).model_dump(
                    mode="python"
                ),
                kind=NAMESPACE + "DdoRichConsolidationPolicy",
                context=context,
            ),
        ),
        source_sets=(
            *tuple(
                FrozenSourceSet.from_selected(name, ())
                for name in (
                    "rich-proposals",
                    "rich-proposal-contexts",
                    "rich-authored-propositions",
                    "rich-known-universe",
                )
            ),
            FrozenSourceSet.from_selected(
                "rich-records", tuple(selected_entry(row) for row in raw)
            ),
            FrozenSourceSet.from_selected(
                "rich-readings",
                tuple(selected_entry(row) for row in resolved) if include_resolution else (),
            ),
            FrozenSourceSet.from_selected(
                "rich-policy-authorizations",
                () if authorization is None else (selected_entry(authorization),),
            ),
        ),
        inference=inference,
    )
    retained = author_interpretations(
        journey.kernel.purpose("write"), journey.kernel.prepared, request=pending
    )
    result = execute_data_demand(
        journey.kernel.purpose("write"),
        retained["demand_id"],
        source_root=ROOT,
        admission_engine=journey.kernel.purpose("admit"),
        project_id=PROJECT,
        database_capacity=6,
    )
    assert result.receipt_count == 2
    cut, products, uses, episodes, _ = journey.selected_products(
        journey.kernel.purpose("read"),
        retained["demand_id"],
        kind=(NAMESPACE + "DdoRichAdmission", NAMESPACE + "DdoRichConsolidation"),
        page_rows=page_rows,
        max_bytes=max_bytes,
    )
    kinds = {
        item.owner: item.key for item in journey.kernel.model.identities if item.domain == "kind"
    }
    ((product, admission),) = [
        item
        for item in products
        if item[0]["kind_contract"] == kinds[NAMESPACE + "DdoRichAdmission"]
    ]
    ((private, consolidation),) = [
        item
        for item in products
        if item[0]["kind_contract"] == kinds[NAMESPACE + "DdoRichConsolidation"]
    ]
    return RichPublication(
        journey,
        retained["demand_id"],
        product,
        DdoRichAdmission.model_validate(admission),
        private,
        DdoRichConsolidation.model_validate(consolidation),
        cut,
        uses,
        episodes,
    )
