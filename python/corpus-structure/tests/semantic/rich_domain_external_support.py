"""Controlled external authoring through actual source, packet, task and CPU custody.

The source decoder and external answers are controlled. The learned sentence provider
and native publication remain real; this does not measure language/model accuracy.
"""

from dataclasses import replace

from evaluate.declared_record_native_support import (
    PROJECT,
    ROOT,
    authored,
    project_context,
    request,
)

from semantic.data_operation_kernel_support import split_captured_operations
from semantic.rich_domain_preservation_support import NS

EXTERNAL = "https://corpus-structure.dev/semantic/data-operation-external-extraction/"


def external_recipe(directory, *, domain="statistics"):
    from evaluate.declared_rich_native_support import rich_policy_recipe

    from corpus_structure.semantic.composed import (
        data_operation_dependencies,
    )
    from corpus_structure.semantic.data_operation_model import ExternalExecutorContract
    from corpus_structure.semantic.declared_math_products import math_operation_declarations
    from corpus_structure.semantic.external_extraction import (
        external_extraction_operation_sources,
        rich_external_declarations,
    )
    from corpus_structure.semantic.primary_operations import combine_primary_sources
    from corpus_structure.semantic.sentence_products import sentence_operation_sources
    from semantic.data_operation_kernel_support import CapturedKernelInputs

    if domain == "toy":
        from semantic.rich_domain_native_support import toy_recipe

        original = toy_recipe(directory)
    else:
        original = rich_policy_recipe(directory)
    captured = original.captured_inputs
    assert captured is not None
    base_dependencies, declarations, sources = split_captured_operations(captured)
    deps = base_dependencies
    protocol = ExternalExecutorContract(
        "external-executor-v1",
        "Return the independently authored controlled domain propositions over the exact native source packet.",
        "controlled-domain-author",
        None,
        "declared-inputs-only",
    )
    deps = data_operation_dependencies(
        deps,
        (*declarations, math_operation_declarations(), rich_external_declarations(protocol)),
        combine_primary_sources(
            sources, sentence_operation_sources(), external_extraction_operation_sources()
        ),
    )
    return replace(
        original,
        name="current-controlled-external-rich-domain",
        captured_inputs=CapturedKernelInputs(captured.bundle, deps, captured.profile),
    )


def publish_external_report(journey, source, response_factory, *, inference):
    """Prepare, claim and fulfill the genuine external task before rich admission."""
    from evaluate.declared_rich_native_support import selected_entry

    from corpus_structure.semantic.data_operation_external import ExternalDataSession
    from corpus_structure.semantic.data_operation_json import json_loads
    from corpus_structure.semantic.data_operation_service import (
        DemandDiscoverySelection,
        DemandRoot,
        execute_data_demand,
    )
    from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet
    from corpus_structure.semantic.data_operation_values import decode_semantic_value
    from corpus_structure.semantic.observations import source_value
    from corpus_structure.semantic.original_documents import acquire_original_document_selection
    from corpus_structure.semantic.rich_knowledge_contracts import (
        DdoRichAdmission,
        DdoRichConsolidation,
    )
    from corpus_structure.semantic.rich_policy_binding import rich_policy_value
    from corpus_structure.serve.interpretation_authoring import author_interpretations
    from semantic.record_publication_native_support import RichPublication

    policy = dict(
        version="external-extraction-policy-1",
        guideline="Controlled domain report over exact native evidence, not model accuracy.",
        known_reference_standing="authored",
        known_classes=source_value({}),
        known_entities=[],
        bootstrap_terms=[],
        macros=source_value({}),
        context_sources=[],
        scope_standing="explicitly-none",
    )
    with journey.kernel.purpose("read").begin() as connection:
        original = acquire_original_document_selection(
            connection, project_id=PROJECT, document_key=source.pin.original_source
        )
    pending = request(
        journey,
        ("source.pdf_views/discovery",),
        (source.context,),
        originals=(
            original.selection(),
            authored(
                journey,
                inference + ":source-policy",
                policy,
                kind=EXTERNAL + "DdoExternalExtractionPolicy",
                context=source.context,
            ),
        ),
        inference=inference + ":source",
    )
    # Existing source roles consume same-demand computed products. Reattach the
    # actual original/source producer and discover child obligations; equal content
    # alone never imports the earlier journey's use or episode into this demand.
    pending = pending.model_copy(
        update=dict(
            roots=(
                DemandRoot(
                    subject=original.root.subject,
                    original_source=original.root.original_source,
                    analyzed_scope=json_loads(original.root.analyzed_scope),
                ),
            ),
            discovery=(
                DemandDiscoverySelection(
                    producer="source.pdf_views/discovery",
                    output_role="result",
                    target="segment.sentences/source-native",
                    population="controlled-external-source-views",
                    target_role="source",
                ),
                DemandDiscoverySelection(
                    producer="source.pdf_views/discovery",
                    output_role="result",
                    target="locate.external_extraction",
                    population="controlled-external-source-views",
                ),
            ),
        )
    )
    retained = author_interpretations(
        journey.kernel.purpose("write"), journey.kernel.prepared, request=pending
    )
    execute_data_demand(
        journey.kernel.purpose("write"),
        retained["demand_id"],
        source_root=ROOT / "python/corpus-structure/src",
        admission_engine=journey.kernel.purpose("admit"),
        project_id=PROJECT,
        database_capacity=6,
    )
    session = ExternalDataSession(
        journey.kernel.purpose("write"), PROJECT, demand_id=retained["demand_id"]
    )
    (header,) = session.queue()["packets"]
    claim = session.claim(header["packet_id"])
    assert claim["state"] == "claimed"
    packet = session.read(header["packet_id"], claim)
    assert packet["packet"]["operation_id"] == "extract.rich_external"
    (entry,) = packet["packet"]["inputs"]
    assert entry["role"] == "packet"
    source_packet = decode_semantic_value(entry["meaning"])
    response = response_factory(journey, source_packet)
    assert response["unit_ref"] == source_packet["unit_ref"]
    completed = session.submit(
        header["packet_id"],
        claim,
        {"outcome": "success", "outputs": [{"role": "authored", "body": response}]},
        actor_assertion="controlled-domain-author",
        model_assertion=None,
    )
    receipt = completed["receipt"]
    assert (
        completed["state"] == "committed"
        and receipt["task_id"] == claim["task_id"]
        and receipt["attempt"] == claim["attempt"]
    )
    assert (
        receipt["actor_assertion"] == "controlled-domain-author"
        and receipt["model_assertion"] is None
    )
    execute_data_demand(
        journey.kernel.purpose("write"),
        retained["demand_id"],
        source_root=ROOT / "python/corpus-structure/src",
        admission_engine=journey.kernel.purpose("admit"),
        project_id=PROJECT,
        database_capacity=6,
    )
    _, products, *_ = journey.selected_products(
        journey.kernel.purpose("read"),
        retained["demand_id"],
        kind=(EXTERNAL + "DdoExternalExtractionPacket", EXTERNAL + "DdoLocatedExternalExtraction"),
    )
    kinds = {
        item.owner: item.key for item in journey.kernel.model.identities if item.domain == "kind"
    }
    ((context_product, _),) = [
        item
        for item in products
        if item[0]["kind_contract"] == kinds[EXTERNAL + "DdoExternalExtractionPacket"]
    ]
    ((proposal_product, proposed),) = [
        item
        for item in products
        if item[0]["kind_contract"] == kinds[EXTERNAL + "DdoLocatedExternalExtraction"]
    ]
    assert all(row["outcome"] in {"produced", "empty"} for row in proposed["coverage"])
    context = project_context(journey, "rich.consolidate")
    final = request(
        journey,
        ("rich.consolidate", "rich.admit"),
        (context,),
        originals=(
            authored(
                journey,
                inference + ":rich-policy",
                rich_policy_value(journey.kernel.prepared, journey.kernel.model).model_dump(
                    mode="python"
                ),
                kind=NS + "DdoRichConsolidationPolicy",
                context=context,
            ),
        ),
        source_sets=(
            FrozenSourceSet.from_selected("rich-proposals", (selected_entry(proposal_product),)),
            FrozenSourceSet.from_selected(
                "rich-proposal-contexts", (selected_entry(context_product),)
            ),
            *tuple(
                FrozenSourceSet.from_selected(name, ())
                for name in (
                    "rich-authored-propositions",
                    "rich-known-universe",
                    "rich-records",
                    "rich-readings",
                    "rich-policy-authorizations",
                )
            ),
        ),
        inference=inference + ":knowledge",
    )
    final_retained = author_interpretations(
        journey.kernel.purpose("write"), journey.kernel.prepared, request=final
    )
    result = execute_data_demand(
        journey.kernel.purpose("write"),
        final_retained["demand_id"],
        source_root=ROOT / "python/corpus-structure/src",
        admission_engine=journey.kernel.purpose("admit"),
        project_id=PROJECT,
        database_capacity=6,
    )
    assert result.receipt_count == 2
    cut, products, uses, episodes, _ = journey.selected_products(
        journey.kernel.purpose("read"),
        final_retained["demand_id"],
        kind=(NS + "DdoRichAdmission", NS + "DdoRichConsolidation"),
    )
    ((product, admission),) = [
        item for item in products if item[0]["kind_contract"] == kinds[NS + "DdoRichAdmission"]
    ]
    ((private, consolidation),) = [
        item for item in products if item[0]["kind_contract"] == kinds[NS + "DdoRichConsolidation"]
    ]
    publication = RichPublication(
        journey,
        final_retained["demand_id"],
        product,
        DdoRichAdmission.model_validate(admission),
        private,
        DdoRichConsolidation.model_validate(consolidation),
        cut,
        uses,
        episodes,
    )
    return publication, receipt, proposed


SOURCE_TEXT = {
    "T1": "For a real a and positive b, let X = a + b Z. This construction is the location-scale family based on Z. The scale parameter b is in (0, infinity).",
    "T2": "Suppose X has the normal distribution with location and scale parameters. The location and scale parameters are the mean and standard deviation, respectively.",
    "T4": "If Y is normal with mean mu and standard deviation sigma, X = exp(Y) is lognormal with parameters mu and sigma. Sigma is its shape parameter; exp(mu) is its scale parameter.",
    "toy": "Filing A and filing B report that Owner owns Asset, attributed to Source, valid from July 2020. A separate report attributes ownership to Other Source. Another report starts in July 2021. Inspector inspected Asset for Custodian: intact, quantity 12.3400 kg on a dry-mass basis.",
}


def controlled_source_response(journey, packet, *, case):
    """Author a controlled external answer over the exact returned packet, not an authored fact."""
    from corpus_structure.semantic.external_extraction import external_extraction_prompt
    from semantic.rich_domain_preservation_support import DomainGraph, t1, t2, t4

    entities = {
        "T1": {"LS": "FamilyConstruction", "scale": "FamilyParameter", "Z": "RandomVariable"},
        "T2": {
            "normal": "DistributionFamily",
            "X": "RandomVariable",
            **{
                key: "FamilyParameter"
                for key in ("location", "scale", "mean", "standard_deviation")
            },
        },
        "T4": {
            "lognormal": "DistributionFamily",
            "normal": "DistributionFamily",
            "Y": "RandomVariable",
            **{key: "FamilyParameter" for key in ("mu", "sigma", "exp_mu_scale")},
        },
        "toy": {
            "owner": "Organization",
            "inspector": "Organization",
            "custodian": "Organization",
            "source": "Source",
            "other-source": "Source",
            "asset": "Asset",
        },
    }[case]
    graph = DomainGraph(
        (
            journey.kernel.prepared,
            journey.kernel.model,
            "ToyQualification" if case == "toy" else "StatisticsQualification",
        ),
        entities,
        context=project_context(journey, "rich.consolidate"),
    )
    if case == "toy":
        from semantic.rich_domain_preservation_support import inspection

        qualification = dict(
            modality="toy:reported",
            polarity=True,
            attribution="source",
            filing_ref="A",
            valid_time=dict(
                kind="validity_interval", start=dict(kind="partial_date", lexical="2020-07")
            ),
        )
        for name, extra in (
            ("A", {}),
            ("B", {"filing_ref": "B"}),
            ("attributed", {"attribution": "other-source"}),
            (
                "dated",
                {
                    "valid_time": dict(
                        kind="validity_interval", start=dict(kind="partial_date", lexical="2021-07")
                    )
                },
            ),
        ):
            graph.add(name, "owner", "owns", "asset", qualification={**qualification, **extra})
        graph.add("inspection", "asset", "inspection", inspection())
    else:
        {"T1": t1, "T2": t2, "T4": t4}[case](graph)
    prompt = external_extraction_prompt(packet)
    evidence = next(item for item in prompt["native_evidence"] if item["text"] == SOURCE_TEXT[case])
    citation = [dict(sentence=evidence["handle"], quote=SOURCE_TEXT[case], role="primary")]
    entity_rows = {
        key: dict(
            id=key, class_iri=graph.prepared.index.definitions[cls].iri, label=key, attributes=[]
        )
        for key, cls in entities.items()
    }
    claims = []
    for key, result in graph.results.items():
        fact = result.fact
        definition = graph.prepared.index.definitions[entities[fact.subject_entity]]
        prop = next(prop for prop in definition.properties if prop.iri == fact.predicate)
        value = graph.object(key)
        value = (
            value.model_dump(mode="python", exclude_unset=True)
            if hasattr(value, "model_dump")
            else (
                dict(kind="entity", target=value)
                if prop.range in graph.prepared.index.definitions
                else dict(kind="text", text=value)
            )
        )
        qualification = graph.qualification(key).model_dump(mode="python", exclude_unset=True)
        row = dict(
            predicate=fact.predicate,
            qualification=qualification,
            establishment="stated",
            evidence=citation,
        )
        if prop.name in {"family", "canonical_name"}:
            entity_rows[fact.subject_entity]["attributes"].append(dict(**row, value=value))
        else:
            claims.append(
                dict(
                    **row,
                    id=key,
                    subject=fact.subject_entity,
                    object=value,
                    statement="controlled-statement",
                    statement_role="conclusion",
                )
            )
    for key, cls in entities.items():
        if cls == "RandomVariable":
            for name, value, establishment in (
                ("symbol", key, "stated"),
                ("scope_locator", packet["unit_ref"], "agent_asserted"),
            ):
                prop = next(
                    prop
                    for prop in graph.prepared.index.definitions[cls].properties
                    if prop.name == name
                )
                entity_rows[key]["attributes"].append(
                    dict(
                        predicate=prop.iri,
                        value=dict(kind="text", text=value),
                        qualification=dict(modality="asserted", polarity=True),
                        establishment=establishment,
                        evidence=citation,
                    )
                )
    return dict(
        unit_ref=packet["unit_ref"],
        entities=list(entity_rows.values()),
        statements=[dict(id="controlled-statement", kind="narrative", anchor=packet["unit_ref"])],
        claims=claims,
        alternatives=[],
        unsupported=[],
        identity_exclusions=[],
    )
