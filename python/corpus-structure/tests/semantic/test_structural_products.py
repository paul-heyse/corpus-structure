"""Independent structural expectations: unknown is not absence or equivalence."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from corpus_structure.methods.structural_products import (
    StructuralProductsConfig, StructuralProductsMethod, assemble_dossier,
    compare_clauses, definition_applicability,
)
from corpus_structure.semantic.structural_products import (
    DIMENSIONS, ClauseField, ClauseReading, DefinitionReading, DossierMember,
    ExternalSourceRef, StructuralInput, StructuralPassage, source_target,
)


def inputs():
    a = ExternalSourceRef(project_id="book-a", run_id=1, cut_id=1, release_id="release:a", result_revision=1, source_view_id=1, native_task_id=1, native_product_key="document", native_content_digest="a"*64, projection_digest="b"*64, recipe_digest="c"*64, coordinate_version=3)
    b = a.model_copy(update={"project_id":"book-b", "run_id":2, "source_view_id":2})
    pa = StructuralPassage(passage_id="a",source_ref=a.identity,start=0,end=5,text="hello",scope="scope")
    pb = StructuralPassage(passage_id="b",source_ref=b.identity,start=10,end=15,text="world",scope="scope")
    return StructuralInput(question="compare source clauses",scope="scope",inventory_id="inventory",policy_id="literal-fields-1",sources=(a,b),passages=(pa,pb),dependencies=("input-policy:1",))


def test_original_projects_do_not_collapse_equal_text_and_source_targets_are_attributed():
    value = inputs()
    assert value.sources[0].identity != value.sources[1].identity
    target = source_target(value.passages[0])
    assert target.type_name == "source_backed_passage"
    assert target.description == "hello"
    assert target.source_binding.startswith("source-passage:")
    with pytest.raises(ValueError,match="project_id"):
        ExternalSourceRef.model_validate({**value.sources[0].model_dump(),"project_id":1})


def test_definition_candidates_do_not_imply_support_or_retrieval_miss():
    value = inputs()
    report = definition_applicability(value,usage_id="a",candidate_list_id="list",eligible_targets=("b",),candidate_targets=("b",),readings=(DefinitionReading(target_id="b",outcome="mention",evidence=("b",),reason="merely mentions the expression"),))
    assert report.definition is not None
    assert report.definition.readings[0].outcome == "mention"
    assert report.definition.retrieval_diagnosis == "not_independently_assessed"
    assert report.standing == "private_proposal"
    with pytest.raises(ValueError,match="outside fixed candidate"):
        definition_applicability(value,usage_id="a",candidate_list_id="list",eligible_targets=("b",),candidate_targets=(),readings=report.definition.readings)


def test_clause_comparison_preserves_ten_dimensions_and_no_equivalence():
    value=inputs()
    left=ClauseReading(passage_id="a",fields=(ClauseField(dimension="modality",lexical_value="must",evidence=("a",)),))
    right=ClauseReading(passage_id="b",fields=(ClauseField(dimension="modality",lexical_value="may",evidence=("b",)),))
    report=compare_clauses(value,left=left,right=right)
    assert report.comparison is not None
    assert tuple(d.dimension for d in report.comparison.dimensions)==DIMENSIONS
    assert [d.outcome for d in report.comparison.dimensions] == ["unknown","unknown","unknown","different_lexical_value","unknown","unknown","unknown","unknown","unknown","unknown"]
    assert report.comparison.identity_standing == report.comparison.equivalence == "not_asserted"
    assert report.product_id.startswith("structural:")
    with pytest.raises(InterruptedError):
        compare_clauses(value,left=left,right=right,cancelled=lambda:True)


def test_parent_scope_is_not_normalized_away():
    value=inputs()
    value=value.model_copy(update={"passages":(value.passages[0],value.passages[1].model_copy(update={"scope":"other"}))})
    left=ClauseReading(passage_id="a",fields=(ClauseField(dimension="action",lexical_value="approve",evidence=("a",)),))
    right=ClauseReading(passage_id="b",fields=(ClauseField(dimension="action",lexical_value="approve",evidence=("b",)),))
    result = compare_clauses(value,left=left,right=right)
    assert result.comparison is not None
    assert result.comparison.dimensions[1].outcome=="incompatible_applicability"


def test_dossier_keeps_all_members_and_mandatory_representatives():
    value=inputs()
    members=tuple(DossierMember(member_id=str(i),passage_id="a" if i%2==0 else "b",role="exception" if i<3 else "usage",sense="sense",scope="scope",relation_product_id="relation:"+str(i)) for i in range(7))
    report=assemble_dossier(value,root_id="sense",members=members)
    assert report.dossier is not None
    assert len(report.dossier.members)==7
    assert set(report.dossier.representatives)>={"0","1","2"}
    assert len(report.dossier.representatives)==4
    assert "definition" in report.dossier.missing_sections
    assert report==assemble_dossier(value,root_id="sense",members=tuple(reversed(members)))
    with pytest.raises(ValueError,match="independent assessment"):
        DossierMember.model_validate({**members[0].model_dump(),"qualification":"independently_supported"})


def test_run_method_and_released_report_roundtrip():
    from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
    from corpus_structure.semantic.observations import bind_result, observation_inputs
    from corpus_structure.core.method import UnitRef
    from corpus_structure.core.vocab import TaskUnitType
    value=inputs()
    report=assemble_dossier(value,root_id="sense",members=())
    cfg=StructuralProductsConfig(report=report,structural_input_digest=value.identity)
    method=StructuralProductsMethod()
    ref=UnitRef(TaskUnitType.RUN,unit_key="run")
    result=method.run((SimpleNamespace(ref=ref),),cfg,None)[0]
    path=Path(__file__).parents[2]/"src/corpus_structure/model/semantic/core.yaml"
    prepared=prepare_release(observation_inputs(SourceBundle("core",(SourceArtifact("core",path.read_bytes()),))))
    bound=bind_result(prepared,source="run",method=method.name,operation_version=method.version,configuration_hash="config",input_hash="input",invocation_key="invocation",result=result)
    payload=bound.model_dump(mode="json")
    assert "records" not in payload
    assert payload["structural_product"]["kind"]=="dossier"
    from corpus_structure.semantic.structural_products import StructuralProductReport
    roundtrip=StructuralProductReport.model_validate(payload["structural_product"])
    assert roundtrip.product_id==report.product_id
    assert roundtrip.inputs.identity==value.identity
    assert method.select(None,StructuralProductsConfig())==[]
