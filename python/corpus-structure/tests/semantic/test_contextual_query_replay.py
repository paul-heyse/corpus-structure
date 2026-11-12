"""Detached query adapters preserve authenticated primary selections and exact signals."""

from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256

import pytest

from corpus_structure.core.evidence import config_key
from corpus_structure.core.method import SourceViewRef
from corpus_structure.methods.contextual_candidates import ContextualQueryConfig
from corpus_structure.methods.contextual_embeddings import E5, identity
from corpus_structure.semantic.contributions import contribution_identity, occurrence_identity, operation_identity
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.source_contexts import record_source_pin
from corpus_structure.serve import contextual_query_replay, primary_characterization_replay, review_bundle
from corpus_structure.serve.contextual_query_replay import query_context_dependency, retained_query_selection

from methods.test_contextual_query import TEXT, anchor, frame_layer, source


def fixture():
    frame=source(); pin=record_source_pin(frame); layers,reference=frame_layer(frame=frame)
    focal=anchor("request",frame=frame); occurrence=occurrence_identity((focal,))
    cfg=ContextualQueryConfig.model_validate(dict(
        source_product_digest=pin["product_digest"], source_projection_digest=pin["projection_digest"], scope="fixture",
        characterization_layers=[reference.layer.values()],
        relationship_constraints=[dict(constraint_id="fixture-denotation",relation_kinds=["denotes"],occurrence_role="observed_source_mention",target_role="retained_definition_component",multiplicity="one",exhaustive=False)],
        target_components=[dict(reference=dict(product_id="fixture-product",component_id="b"*64,operation_id="structure.definition_components",operation_version="9",project_id="project",release_id="release",run_id=3,cut_id=4,result_revision=4,selected_task_id=5,origin_task_id=5,runtime_fingerprint="runtime",dependencies=["source"]),label="request",description="a document awaiting review",scope="fixture")],
        query_context=dict(recipe="located-frame-2",bindings=[dict(occurrence_id=occurrence,evidence=reference.values())]),
    )).model_dump(mode="json")
    key=operation_identity("retrieve.contextual","12",cfg,pin)
    carrier=dict(pin=pin,kind="occurrence",semantic_type="contextual.located_mention",item_key="focal",anchors=[focal],occurrence_id=occurrence,operation_key=key)
    carrier["contribution_id"]=contribution_identity(carrier)
    receipt=dict(recipe="located-frame-2",evidence=reference.values(),signals=[
        dict(label="Predicate",anchor_ids=[anchor("approves",frame=frame)["anchor_id"]]),
        dict(label="Argument direct_object",anchor_ids=[anchor("the request",frame=frame)["anchor_id"]]),
    ],omissions=["Argument subject has no exact source location"])
    representation=identity("located-query-context",receipt)
    text="Mention: request\nType: unknown\nPredicate: approves\nArgument direct_object: the request\nContext: "+TEXT
    rendered=dict(object_id=occurrence,source_binding=pin["source"],role="query",text=text,truncated=False,representation_digest=representation,final_input_digest=sha256((E5.query_prompt+text).encode()).hexdigest())
    binding=[occurrence,pin["source"],E5.profile_id,rendered["final_input_digest"],representation]
    vector=dict(vector_id=identity("context-vector",binding),object_id=occurrence,source_binding=pin["source"],profile_id=E5.profile_id,input_digest=rendered["final_input_digest"],representation_digest=representation,values=[1.0,*([0.0]*(E5.dimension-1))])
    report=dict(origin_task_id=21,origin_unit_id=1,unit_type="source_view",project_id="project",method="retrieve.contextual",configuration=cfg,origin_run_id=19,runtime_fingerprint="runtime",body=dict(source=pin["source"],operation_version="12",release_id="release",configuration_hash=config_key("retrieve.contextual","12",cfg),contributions=[carrier],parse_detail=source_value(dict(query_context={occurrence:dict(receipt,outcome="rendered")},encoder_inputs=[rendered])),contribution_operations=[dict(operation_key=key,operation_version="12",outcome="succeeded",question="retained producer occurrence roles and contextual encoder products",computation_dependencies=[reference.identity],contextual_enrichment=dict(vectors=[vector]))]))
    context=__import__('json').loads(frame.native_context)
    assert frame.membership == "direct"
    ref = SourceViewRef(
        id=frame.source_view_id,
        key=frame.unit_ref,
        document_id=1,
        native_product=frame.native_product,
        section_pointer=frame.section_pointer,
        membership="direct",
        projection_digest=frame.projection_digest,
        recipe_digest=frame.recipe_digest,
        analysis_eligible=True,
    )
    captured=dict(source_view_id=1,ref=asdict(ref),text=frame.text,context=context)
    return report,layers,captured,receipt,rendered,vector


@pytest.mark.parametrize("substitution",[None,"selection","receipt","render","vector","source","dependency"])
def test_detached_v12_query_replays_primary_signal_after_shared_authentication(monkeypatch,substitution):
    report,layers,captured,receipt,rendered,vector=fixture()
    occurrence=report["body"]["contributions"][0]["occurrence_id"]
    if substitution=="selection":layers={}
    elif substitution=="receipt":receipt["signals"][1]["anchor_ids"]=receipt["signals"][0]["anchor_ids"]
    elif substitution=="render":
        rendered["text"]=rendered["text"].replace("Argument direct_object:","Argument subject:")
        rendered["final_input_digest"]=sha256((E5.query_prompt+rendered["text"]).encode()).hexdigest()
    elif substitution=="vector":vector["representation_digest"]="foreign"
    elif substitution=="source":captured["ref"]["projection_digest"]="e"*64
    elif substitution=="dependency":report["body"]["contribution_operations"][0]["computation_dependencies"]=[]
    report["body"]["parse_detail"]=source_value(dict(query_context={occurrence:dict(receipt,outcome="rendered")},encoder_inputs=[rendered]))
    # These adapter controls begin after the shared immutable layer/archive/source
    # authenticator. They neither fake provider passage nor replace its independent tests.
    monkeypatch.setattr(primary_characterization_replay,"retained_primary_layers",lambda *_:(layers,{}))
    monkeypatch.setattr(review_bundle,"_detached_relation",lambda _root,_manifest,name:iter([report] if name=="reports" else [captured] if name=="sources" else []))
    scopes={0:dict(project_id="project",binding=dict(release_id="release"))}
    inventory={(0,21,21):dict(cut_member=True,origin_project_id="project",origin_run_id=19,source_view_id=1,runtime_fingerprint="runtime")}
    call=lambda:contextual_query_replay.verify_contextual_query_closure(None,{},scopes,{},inventory)
    if substitution:
        with pytest.raises(ValueError):call()
    else:
        selection=retained_query_selection("retrieve.contextual","12",report["configuration"])
        assert selection is not None
        assert call()=={canonical_bytes(query_context_dependency(21,selection.bindings[0].evidence))}


def test_obsolete_query_arms_require_regeneration_but_literal_controls_remain_readable():
    report,*_=fixture(); cfg=report["configuration"]
    with pytest.raises(ValueError,match="regeneration"):
        retained_query_selection("retrieve.contextual","11",cfg)
    literal=deepcopy(cfg);literal.pop("query_context")
    literal["required_occurrence_ids"]=[report["body"]["contributions"][0]["occurrence_id"]]
    assert retained_query_selection("retrieve.contextual","11",literal) is None
    assert retained_query_selection("retrieve.contextual","12",literal) is None
    literal["required_occurrence_ids"]*=2
    with pytest.raises(ValueError,match="distinct"):
        retained_query_selection("retrieve.contextual","12",literal)
