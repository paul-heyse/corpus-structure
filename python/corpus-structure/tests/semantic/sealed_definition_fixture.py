"""Finite sealed definition packets for native reader/corruption controls.

These fixtures author controlled native responses and call shared pure decoders;
they acquire no model, execute no production method and schedule no work.
"""

from dataclasses import asdict
import json
from types import SimpleNamespace
from typing import Literal

from corpus_structure.core.method import Resources, UnitResult
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType


def component_descriptor():
    from corpus_structure.methods.definition_applicability import DefinitionComponentsConfig

    return SimpleNamespace(name="structure.definition_components", version="10", family=MethodFamily.RESOLVE, tier=MethodTier.ENCODER, unit_type=TaskUnitType.RUN, confidence_source=None, Config=DefinitionComponentsConfig, resources=Resources(worker="cpu", batch_size=1, max_concurrency=1))


def applicability_descriptor():
    from corpus_structure.methods.definition_applicability import DefinitionApplicabilityConfig

    return SimpleNamespace(name="structure.definitions", version="2", family=MethodFamily.RESOLVE, tier=MethodTier.DETERMINISTIC, unit_type=TaskUnitType.RUN, confidence_source=None, Config=DefinitionApplicabilityConfig, resources=Resources())


def controlled_component_result(prepared, configuration, ref, raw):
    from corpus_structure.methods.definition_applicability import decode_definition_components, located_definition_roles
    from corpus_structure.methods.gliner import GlinerInput, GlinerPreparation, GlinerReport
    from corpus_structure.methods.model_observation import batch_receipt, observation_digest, released_pack, released_policy
    from corpus_structure.methods.predicate_frames import PREDICATE_FRAME_VERSION
    from corpus_structure.semantic.structural_products import DefinitionComponentsProduct, DefinitionStage, StructuralProductReport

    inputs, profile = configuration.inputs, configuration.profile
    if inputs is None or profile is None or len(configuration.target_ids) != 1:
        raise ValueError("sealed component fixture requires one exact authored target")
    passage = next(value for value in inputs.passages if value.passage_id == configuration.target_ids[0])
    policy = released_policy(prepared)
    config = configuration.model_dump(mode="json")
    pack = released_pack(prepared.release_id, policy, config=config)
    request = GlinerInput("definition-target:" + passage.identity, passage.identity, passage.text, "structure.definition_components/10")
    receipt = batch_receipt(pack, asdict(profile), (request,), configuration.threshold, "flat", False, policy["inference"])
    digest = receipt["digest"]
    raw_json = json.dumps(raw)
    envelope = GlinerReport(request.context_id, request.context_digest, digest, profile.fingerprint, pack.fingerprint, GlinerPreparation(request.text, "", 1, 1, len(request.text.encode())), raw_json, "{}", 0.0, False, request_digest=digest, observation_digest=observation_digest(digest, raw_json, "{}", ordinal=0, member=receipt["members"][0]), batch_receipt_json=json.dumps(receipt), member_ordinal=0)
    candidate_errors, role_errors = [], []
    components = decode_definition_components(raw, passage, configuration, candidate_errors=candidate_errors)
    roles = located_definition_roles(raw, passage, configuration, envelope=digest, errors=role_errors)
    report = StructuralProductReport(kind="definition_components", inputs=inputs, definition_components=DefinitionComponentsProduct(components=components, role_candidates=roles, stages=(DefinitionStage(passage_id=passage.passage_id, operation="located_extraction", outcome="failed" if role_errors else "succeeded" if roles else "empty", reason="Independently authored exact endpoint roles."), DefinitionStage(passage_id=passage.passage_id, operation="attachment", outcome="failed" if candidate_errors else "succeeded" if components else "empty", reason="Independently authored directed relation between those exact endpoints."))))
    detail = dict(version="located-definition-extraction-5", predicate_frame_version=PREDICATE_FRAME_VERSION, raw_reports=[dict(passage_id=passage.passage_id, window_start=passage.start, window_end=passage.end, **asdict(envelope), decoded_attachment_count=len(components), candidate_errors=candidate_errors)], window_outcomes=[dict(passage_id=passage.passage_id, start=passage.start, end=passage.end, request_digest=digest, status="returned")], named_rule_operations=[], annotation_inputs=[], pack_fingerprint=pack.fingerprint, schema_declaration=pack.declaration_json, profile_fingerprint=profile.fingerprint, profile=config["profile"], description_arm="bare", overlap_policy="flat")
    return UnitResult(ref=ref, outcome=ObservationOutcome.PRODUCED, structural_product=report.model_dump(mode="json"), parse_detail=detail)



def literal_component_result(prepared, configuration, ref):
    if configuration.inputs is None or configuration.target_ids != ("literal",):
        raise ValueError("sealed numeral fixture requires its actual literal input")
    (passage,) = configuration.inputs.passages
    if passage.text != "12" or (passage.start, passage.end) != (0, 2):
        raise ValueError("sealed numeral fixture is only the independently authored 12")
    endpoint = dict(start=0, end=2, text="12")
    raw = dict(entities={"defined term or expression": [dict(endpoint, interpretation="definition")], "defining text or formula": [endpoint]}, relation_extraction={"term is defined or explained by": [dict(head=endpoint, tail=endpoint)]})
    return controlled_component_result(prepared, configuration, ref, raw)


def applicability_result(configuration, ref, *, component, component_reference, relationship_reference, decision, edge):
    from corpus_structure.methods.definition_applicability import ApplicabilityCandidate, assess_applicability, is_defining_occurrence
    from corpus_structure.semantic.structural_products import ApplicabilityPremise, DefinitionProduct, StructuralProductReport

    inputs, usage_id = configuration.inputs, configuration.usage_id
    if inputs is None or usage_id is None or configuration.selection_refs != (relationship_reference,):
        raise ValueError("sealed applicability requires its actual single retained relationship")
    usage = next(passage for passage in inputs.passages if passage.passage_id == usage_id)
    if edge["relation"] not in {"denotes", "defined-by"} or decision["scope"] != usage.scope or decision.get("effective_version") != usage.effective_version or component.component_id not in edge["member_target_ids"]:
        raise ValueError("sealed applicability fixture differs from its actual retained meaning/carrier")
    introduction = configuration.applicability_scope == "defining_occurrence" and is_defining_occurrence(inputs, usage, component, edge["relation"])
    transfer_dimensions: tuple[Literal["parameterization", "convention"], ...] = ("parameterization", "convention")
    candidate = ApplicabilityCandidate(target_id=edge["target_id"], reference=component_reference, link_ref=relationship_reference, component=component, premises=(ApplicabilityPremise(dimension="sense", state="compatible", evidence=(usage_id, component.term.passage_id), reason="Actual selected usage relationship; independent semantic support remains separate."), *(ApplicabilityPremise(dimension=dimension, state="inapplicable" if introduction else "unknown", evidence=(usage_id, component.term.passage_id), reason="The independently selected introduction requires no transfer." if introduction else "No authenticated transfer correspondence has been established.") for dimension in transfer_dimensions)))
    reading = assess_applicability(inputs, usage_id, candidate, defining_occurrence=introduction)
    report = StructuralProductReport(kind="definition_applicability", inputs=inputs, definition=DefinitionProduct(usage_id=usage_id, candidate_list_id=decision["candidate_list_id"], eligible_targets=(edge["target_id"],), candidate_targets=(edge["target_id"],), readings=(reading,)))
    return UnitResult(ref=ref, outcome=ObservationOutcome.PRODUCED, structural_product=report.model_dump(mode="json"))
