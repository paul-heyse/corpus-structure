"""Exact component eligibility through real independent-pass and publication owners.

The authored interpretations are controlled mechanism inputs, not corpus quality evidence.
"""

from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from corpus_structure.semantic.refusals import SemanticRefusal
import pytest

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.evaluate.record_references import assign_origin
from corpus_structure.evaluate.structural_assessment import (
    StructuralAuthoredReference, StructuralEvaluationFrame, StructuralReferenceCase,
    StructuralSourceGroup, StructuralSourceOpportunity, create_structural_reference_set,
    record_structural_reference_pass,
)
from corpus_structure.methods.structural_products import StructuralProductsMethod
from corpus_structure.orchestrate import semantic
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding
from .native_record_fixtures import private_source as private_source
from .native_record_fixtures import private_source_options as private_source_options
from .test_contextual_workflow_native import completed_component_case


def test_exact_component_admits_without_whole_applicability(private_source, semantic_evaluator_engine, tmp_path):
    case = private_source
    completed = completed_component_case(case, tmp_path)
    source = completed.source
    # Literal expectations are authored independently of the production statement projector.
    citation = dict(source=dict(project_id="private-records", native_product_key=source.native_product_key,
        native_content_digest=source.native_content_digest, projection_digest=source.projection_digest,
        recipe_digest=source.recipe_digest, coordinate_version=2), start=0, end=2, text="12", scope="controlled-source")
    expected = dict(version="structural-public-statement-2", kind="definition_components",
        scope="controlled-source", inventory_id="controlled-original-source", input_policy_id="controlled-component-1",
        coverage_limits=[], exclusions=[], definition_component=dict(term=citation, content=citation,
        interpretation="definition", basis="native_geometry", scope="controlled-source", alternatives=[]))
    frozen = StructuralEvaluationFrame(inputs=completed.inputs, operation="definition_components",
        direction="source_first", rubric_version="independent-definition-component-1",
        rubric_text="Controlled exact located attachment only, no usage applicability or semantic-quality claim.",
        partition="development", source_groups=(StructuralSourceGroup(source_ref=source.identity, origin_group="controlled-source"),),
        opportunities=(StructuralSourceOpportunity(opportunity_id="attachment",passage_id="literal",facet="attachment",source_state="stated"),), inspected_scope="literal")
    reference = StructuralAuthoredReference(frame_digest=frozen.identity, cases=(StructuralReferenceCase(
        case_id="attachment", component_id=completed.component.component_id, facet="public_statement",
        path=("public_statement",), expected=expected, source_passages=("literal",), judgment="supported",
        explanation="Controlled exact authority input; stronger applicability is unassessed."),))
    with semantic_evaluator_engine.begin() as conn:
        assign_origin(conn,project_id="private-records",origin_group="controlled-source",partition="development",source_uris=("source.pdf",),provenance={"kind":"controlled-native-fixture"})
        set_id=create_structural_reference_set(conn,project_id="private-records",release_id=case.prepared.release_id,frame=frozen)
        payload=canonical_bytes(reference.model_dump(mode="json",exclude_none=True))
        a=record_structural_reference_pass(conn,set_id=set_id,pass_kind="A",actor="independent-a",authored=payload)
        b=record_structural_reference_pass(conn,set_id=set_id,pass_kind="B",actor="independent-b",authored=payload)
        c=record_structural_reference_pass(conn,set_id=set_id,pass_kind="C",actor="independent-c",authored=payload,parents=(a,b))
        digest=conn.scalar(select(table("eval.structural_reference_pass").c.content_digest).where(table("eval.structural_reference_pass").c.id==c))
    admission=dict(product_id=completed.report.product_id,component_id=completed.component.component_id,
        set_id=set_id,c_pass_id=c,c_content_digest=digest,frame_digest=frozen.identity,policy_id="independent-definition-component-1")

    def produce(binding, output):
        run=semantic.run_source_methods(case.writer,project_id="private-records",prepared=case.prepared,
            binding=OperationBinding(case.prepared.release_id,"wce-source",completed.source_revision,b"{}"),
            registry=MethodRegistry([StructuralProductsMethod()],MethodsFile(configs={"structure.products":{"default":dict(report=completed.report.model_dump(mode="json"),structural_input_digest=completed.inputs.identity)}})),
            graph=Graph(((Stage.ASSEMBLE,(Step("structure.products/default"),)),),policy_propose=False),
            structural_admission=(binding,),method_settings=MethodSettings(data_dir=tmp_path,model_cache=tmp_path))
        finalize_bound_run(case.writer,run.run_id,output)
        return run.run_id

    run=produce(admission,"component-publication")
    with case.writer.connect() as conn:
        rows=conn.execute(select(table("data.structural_assertion")).where(table("data.structural_assertion").c.realization_id=="component-publication")).mappings().all()
    assert len(rows)==1
    assert rows[0]["policy_id"]=="independent-definition-component-1"
    assert rows[0]["statement_json"]==canonical_bytes(expected).decode()
    # Changing the requested authority cannot borrow the component's supported event.
    with pytest.raises((DBAPIError,SemanticRefusal),match="policy|structural|publication"):
        produce(dict(admission,policy_id="independent-witnessed-applicability-1"),"refused-whole-applicability")
