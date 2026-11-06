"""Independent endpoint, role and compatibility controls; no mocked efficacy claims."""

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from corpus_structure.methods.annotation_rules import AnnotationRuleMatch, LocatedRole
from corpus_structure.methods.definition_applicability import (
    ApplicabilityCandidate, DefinitionApplicabilityConfig, DefinitionApplicabilityMethod,
    DefinitionComponentsConfig, DefinitionComponentsMethod, assess_applicability,
    components_from_named_matches, decode_definition_components, definition_pack,
)
from corpus_structure.methods.gliner import GlinerProfile, GlinerRefused
from corpus_structure.semantic.contextual_links import RetainedRelationshipDecisionRef
from corpus_structure.semantic.structural_admission import structural_statement
from corpus_structure.semantic.structural_products import (
    ApplicabilityPremise, DefinitionComponentsProduct, ExternalSourceRef,
    RetainedComponentRef, StructuralInput, StructuralPassage, StructuralProductReport,
)


def inputs(text="We call the expected squared deviation variance."):
    source = ExternalSourceRef(project_id="book",run_id=1,cut_id=1,release_id="r",result_revision=1,source_view_id=1,native_task_id=1,native_product_key="native",native_content_digest="a"*64,projection_digest="b"*64,recipe_digest="c"*64,coordinate_version=3)
    return StructuralInput(question="What is defined?",scope="s",inventory_id="i",policy_id="p",sources=(source,),passages=(StructuralPassage(passage_id="target",source_ref=source.identity,start=10,end=10+len(text),text=text,scope="s"),StructuralPassage(passage_id="usage",source_ref=source.identity,start=100,end=108,text="variance",scope="s")),dependencies=("source","structural:component-report"))


def raw(text):
    term = {"start":text.index("variance"),"end":text.index("variance")+8,"text":"variance","interpretation":"definition"}
    content = {"start":text.index("expected"),"end":text.index(" deviation")+10,"text":"expected squared deviation"}
    return {"entities":{"defined term or expression":[term],"defining text or formula":[content]},"relation_extraction":{"term is defined or explained by":[{"head":{k:v for k,v in term.items() if k != "interpretation"},"tail":content}]}}


def component():
    value=inputs()
    return decode_definition_components(raw(value.passages[0].text),value.passages[0],DefinitionComponentsConfig())[0]


def reference():
    return RetainedComponentRef(product_id="structural:component-report",component_id=component().component_id,operation_id="structure.definition_components",operation_version="1",project_id="book",run_id=1,cut_id=1,release_id="r",result_revision=1,selected_task_id=1,origin_task_id=1,runtime_fingerprint="runtime",dependencies=("source",))


def link_reference():
    return RetainedRelationshipDecisionRef(project_id="book",run_id=1,cut_id=1,release_id="r",result_revision=1,selected_task_id=2,origin_task_id=2,runtime_fingerprint="runtime",operation_key="operation",decision_id="decision",edge_id="edge",occurrence_contribution_id="occurrence")


def premises(state="compatible"):
    return tuple(ApplicabilityPremise(dimension=d,state=state if d=="sense" else "inapplicable",evidence=("usage","target"),reason="Independently specified literal compatibility test.") for d in ("sense","parameterization","convention"))


def test_absent_operations_cannot_smuggle_partial_inputs():
    assert DefinitionComponentsMethod().select(None,DefinitionComponentsConfig()) == ()
    assert DefinitionApplicabilityMethod().select(None,DefinitionApplicabilityConfig()) == ()
    with pytest.raises(ValueError,match="partial"):
        DefinitionComponentsConfig(target_ids=("target",))


def test_target_local_pack_qualifies_attributes_without_whole_pair_labels():
    schema=definition_pack("r",DefinitionComponentsConfig()).compile().to_dict()
    assert schema["entity_attributes"]["interpretation"]["applies_to"] == ["defined term or expression"]
    assert "classifications" not in schema


def test_reversed_surface_order_retains_correct_original_endpoints():
    c=component()
    assert (c.term.text,c.content.text)==("variance","expected squared deviation")
    assert c.content.start < c.term.start
    assert c.term.start==49 and c.content.start==22
    assert c.basis=="model_reading"


def test_unattached_span_does_not_invent_definition_or_role():
    value=inputs(); returned=raw(value.passages[0].text)
    returned["relation_extraction"]={}
    assert decode_definition_components(returned,value.passages[0],DefinitionComponentsConfig()) == ()
    returned=raw(value.passages[0].text); returned["entities"]["defined term or expression"][0]["text"]="sigma"
    with pytest.raises(GlinerRefused,match="slice"):
        decode_definition_components(returned,value.passages[0],DefinitionComponentsConfig())


def test_missing_span_attribute_is_unavailable_not_a_default_definition():
    value=inputs(); returned=raw(value.passages[0].text)
    del returned["entities"]["defined term or expression"][0]["interpretation"]
    with pytest.raises(GlinerRefused,match="interpretation"):
        decode_definition_components(returned,value.passages[0],DefinitionComponentsConfig())


def test_component_closure_rejects_relocated_text_and_old_report_protocol():
    value=inputs(); c=component()
    report=StructuralProductReport(kind="definition_components",inputs=value,definition_components=DefinitionComponentsProduct(components=(c,),stages=()))
    with pytest.raises(ValueError):
        StructuralProductReport.model_validate({**report.model_dump(),"version":"structural-product-1"})
    with pytest.raises(ValueError,match="original passage"):
        StructuralProductReport(kind="definition_components",inputs=value.model_copy(update={"passages":(value.passages[0].model_copy(update={"text":"X"*len(value.passages[0].text)}),value.passages[1])}),definition_components=report.definition_components)
    with pytest.raises(ValueError,match="selector"):
        structural_statement(report)
    statement=structural_statement(report,c.component_id)
    assert statement["definition_component"]["term"]["text"]=="variance"
    assert statement["definition_component"]["content"]["start"]==22


def test_applicability_is_separate_and_unknown_premises_preserve_component():
    candidate=ApplicabilityCandidate(target_id="target",reference=reference(),link_ref=link_reference(),component=component(),premises=premises("unknown"))
    assert assess_applicability(inputs(),"usage",candidate).outcome=="unresolved"
    assert candidate.component.term.text=="variance"
    assert assess_applicability(inputs(),"usage",candidate.model_copy(update={"premises":premises()})).outcome=="applicable_definition"
    assert assess_applicability(inputs(),"usage",candidate.model_copy(update={"premises":premises("incompatible")})).outcome=="incompatible"


def test_named_roles_use_bindings_not_surface_order():
    passage=inputs().passages[0]
    term=LocatedRole("term","last",5,"exact",(5,),((49,57),),"complete")
    content=LocatedRole("content","first",2,"subtree",(2,3,4),((22,30),(31,38),(39,48)),"complete")
    match=AnnotationRuleMatch("call","reversed","dependency",(5,2),((22,56),),(),(),"d",(content,term))
    found=components_from_named_matches(passage,(match,),term_role="term",content_role="content")
    assert len(found)==1 and found[0].term.text=="variance"
    unavailable=replace(match,roles=(replace(term,status="unavailable"),content))
    assert components_from_named_matches(passage,(unavailable,),term_role="term",content_role="content")==()


def test_following_display_requires_explicit_cue_and_direct_native_element():
    from corpus_structure.methods.definition_applicability import components_from_following_display
    value=inputs("Density is defined as follows:\nf(x)=x.")
    passage=value.passages[0]
    term=LocatedRole("defined_term","term",0,"noun_chunk",(0,),((10,17),),"complete")
    cue=LocatedRole("following_content_cue","cue",4,"exact",(4,),((32,39),),"complete")
    match=AnnotationRuleMatch("defining","follows","dependency",(0,4),((10,39),),(),(),"d",(term,cue))
    found=components_from_following_display(passage,(match,),((41,48),),term_role="defined_term")
    assert len(found)==1 and found[0].term.text=="Density" and found[0].content.text=="f(x)=x."
    assert found[0].basis=="native_geometry"
    assert components_from_following_display(passage,(replace(match,roles=(term,)),),((41,48),),term_role="defined_term")==()
    # A non-adjacent display cannot be attached across intervening prose.
    assert components_from_following_display(passage,(match,),((43,48),),term_role="defined_term")==()
