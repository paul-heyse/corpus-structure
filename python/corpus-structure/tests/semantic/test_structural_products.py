"""Independent current structural expectations: unknown is not absence or equivalence.

The real declared producer/native issuer journeys own release and execution custody;
these supplied qualified pure inputs establish neither.
"""

import pytest

from corpus_structure.methods.structural_products import compare_clauses, select_dossier
from corpus_structure.semantic.declared_structural_references import DeclaredStructuralSource
from corpus_structure.semantic.structural_products import (
    DIMENSIONS, DeclaredClauseField, DeclaredClauseFieldGroup, DeclaredClauseReading,
    DeclaredDossierMember, LocatedDefinitionSpan,
)
from semantic.structural_products_support import inputs, root_references


def reading(value, index, dimension, literal):
    passage = value.passages[index]
    start = passage.start + passage.text.index(literal)
    groups = {name: DeclaredClauseFieldGroup(state="unresolved") for name in DIMENSIONS}
    groups[dimension] = DeclaredClauseFieldGroup(state="present", grouping="singleton", members=(
        DeclaredClauseField(dimension=dimension, lexical_value=literal, evidence=(passage.passage_id,),
            span=LocatedDefinitionSpan(passage_id=passage.passage_id, start=start, end=start+len(literal), text=literal)),))
    source = next(source for source in value.sources if source.identity == passage.source_ref)
    reference = dict(contribution_id="source-contribution:" + str(index + 1)*64,
        product_id=f"fixture:reading:{index}", kind_contract="kind:fixture-reading",
        project_id=source.project_id, subject=source.subject, subject_definition=source.subject_definition,
        original_source=source.original_source, analyzed_scope_meaning=source.analyzed_scope_meaning)
    return DeclaredClauseReading(passage_id=passage.passage_id, groups=groups), reference


def comparison(value, dimension, left_literal, right_literal, **kwargs):
    left, left_ref = reading(value, 0, dimension, left_literal)
    right, right_ref = reading(value, 1, dimension, right_literal)
    return compare_clauses(value, left=left, right=right, left_reading=left_ref, right_reading=right_ref, **kwargs)


def test_original_projects_do_not_collapse_equal_text():
    value = inputs("same", "same", starts=(0, 0))
    assert value.sources[0].identity != value.sources[1].identity
    assert value.sources[0].original_source != value.sources[1].original_source
    with pytest.raises(ValueError, match="project_id"):
        DeclaredStructuralSource.model_validate({**value.sources[0].model_dump(), "project_id": 1})


def test_clause_comparison_preserves_ten_dimensions_and_no_equivalence():
    value = inputs("Manager must approve.", "Manager may approve.", starts=(0, 0))
    report = comparison(value, "modality", "must", "may")
    assert report.comparison is not None
    assert tuple(d.dimension for d in report.comparison.dimensions) == DIMENSIONS
    assert [d.outcome for d in report.comparison.dimensions] == [
        "unknown", "unknown", "unknown", "different_lexical_value", "unknown",
        "unknown", "unknown", "unknown", "unknown", "unknown"]
    assert report.comparison.identity_standing == report.comparison.equivalence == "not_asserted"
    assert report.product_id.startswith("structural:")
    with pytest.raises(InterruptedError):
        comparison(value, "modality", "must", "may", cancelled=lambda: True)


def test_parent_scope_is_not_normalized_away():
    value = inputs("approve", "approve", starts=(0, 0))
    value = value.model_copy(update={"passages": (value.passages[0], value.passages[1].model_copy(update={"scope": "other"}))})
    report = comparison(value, "action", "approve", "approve")
    assert report.comparison is not None
    assert report.comparison.dimensions[1].outcome == "incompatible_applicability"
    left_group, right_group = report.comparison.dimensions[1].left_group, report.comparison.dimensions[1].right_group
    assert left_group is not None and right_group is not None
    assert left_group.members[0].lexical_value == right_group.members[0].lexical_value == "approve"
    assert report.comparison.applicability == "differently_scoped"


def test_dossier_keeps_all_members_and_mandatory_representatives():
    value = inputs()
    root, predecessor = root_references(value)
    members = tuple(DeclaredDossierMember(
        member_id=str(i), passage_id=value.passages[i%2].passage_id,
        citation=LocatedDefinitionSpan(passage_id=value.passages[i%2].passage_id,
            start=value.passages[i%2].start, end=value.passages[i%2].end, text=value.passages[i%2].text),
        role="exception" if i<3 else "usage", sense=root.component_id, scope="scope",
        relation_product_id="relation:"+str(i)) for i in range(7))
    def select(rows):
        return select_dossier(value, root_id=root.component_id, root_component=root,
            predecessors=(predecessor,), members=rows, member_budget=4)
    report = select(members)
    assert report.dossier is not None and len(report.dossier.members) == 7
    assert set(report.dossier.representatives) >= {"0", "1", "2"}
    assert len(report.dossier.representatives) == 4
    assert "definition" in report.dossier.missing_sections
    assert report == select(tuple(reversed(members)))
    with pytest.raises(ValueError, match="independent assessment"):
        DeclaredDossierMember.model_validate({**members[0].model_dump(), "qualification": "independently_supported"})
