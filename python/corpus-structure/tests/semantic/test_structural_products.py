"""Independent structural expectations: unknown is not absence or equivalence."""

from types import SimpleNamespace

import pytest

from corpus_structure.methods.structural_products import (
    StructuralComparisonConfig,
    StructuralComparisonMethod,
    compare_clauses,
    select_dossier,
)
from corpus_structure.semantic.structural_products import (
    DIMENSIONS,
    ClauseField,
    ClauseReading,
    DossierMember,
    ExternalSourceRef,
    LocatedDefinitionSpan,
    definition_component,
    legacy_structural_sources,
)
from semantic.structural_products_support import inputs as inputs


def fixture_component():
    passage = inputs().passages[1]
    span = LocatedDefinitionSpan(
        passage_id=passage.passage_id, start=passage.start, end=passage.end, text=passage.text
    )
    return definition_component(
        term=span,
        content=span,
        interpretation="definition",
        basis="model_reading",
        scope=passage.scope,
        evidence=(passage.passage_id,),
        reason="Literal shape fixture",
    )


def test_original_projects_do_not_collapse_equal_text():
    value = inputs()
    assert (
        legacy_structural_sources(value)[0].identity != legacy_structural_sources(value)[1].identity
    )
    with pytest.raises(ValueError, match="project_id"):
        ExternalSourceRef.model_validate(
            {**legacy_structural_sources(value)[0].model_dump(), "project_id": 1}
        )


def test_comparison_config_rejects_supplied_report():
    with pytest.raises(ValueError):
        StructuralComparisonConfig.model_validate({"report": {}})


def test_clause_comparison_preserves_ten_dimensions_and_no_equivalence():
    value = inputs()
    left = ClauseReading(
        passage_id="a",
        fields=(ClauseField(dimension="modality", lexical_value="must", evidence=("a",)),),
    )
    right = ClauseReading(
        passage_id="b",
        fields=(ClauseField(dimension="modality", lexical_value="may", evidence=("b",)),),
    )
    report = compare_clauses(value, left=left, right=right)
    assert report.comparison is not None
    assert tuple(d.dimension for d in report.comparison.dimensions) == DIMENSIONS
    assert [d.outcome for d in report.comparison.dimensions] == [
        "unknown",
        "unknown",
        "unknown",
        "different_lexical_value",
        "unknown",
        "unknown",
        "unknown",
        "unknown",
        "unknown",
        "unknown",
    ]
    assert report.comparison.identity_standing == report.comparison.equivalence == "not_asserted"
    assert report.product_id.startswith("structural:")
    with pytest.raises(InterruptedError):
        compare_clauses(value, left=left, right=right, cancelled=lambda: True)


def test_parent_scope_is_not_normalized_away():
    value = inputs()
    value = value.model_copy(
        update={
            "passages": (value.passages[0], value.passages[1].model_copy(update={"scope": "other"}))
        }
    )
    left = ClauseReading(
        passage_id="a",
        fields=(ClauseField(dimension="action", lexical_value="approve", evidence=("a",)),),
    )
    right = ClauseReading(
        passage_id="b",
        fields=(ClauseField(dimension="action", lexical_value="approve", evidence=("b",)),),
    )
    result = compare_clauses(value, left=left, right=right)
    assert result.comparison is not None
    assert result.comparison.dimensions[1].outcome == "same_lexical_value"
    assert result.comparison.applicability == "differently_scoped"


def test_dossier_keeps_all_members_and_mandatory_representatives():
    value = inputs()
    members = tuple(
        DossierMember(
            member_id=str(i),
            passage_id="a" if i % 2 == 0 else "b",
            citation=LocatedDefinitionSpan(
                passage_id="a" if i % 2 == 0 else "b",
                start=0 if i % 2 == 0 else 10,
                end=5 if i % 2 == 0 else 15,
                text="hello" if i % 2 == 0 else "world",
            ),
            role="exception" if i < 3 else "usage",
            sense="sense",
            scope="scope",
            relation_product_id="relation:" + str(i),
        )
        for i in range(7)
    )
    report = select_dossier(value, root_id="sense", members=members, member_budget=4)
    assert report.dossier is not None
    assert len(report.dossier.members) == 7
    assert set(report.dossier.representatives) >= {"0", "1", "2"}
    assert len(report.dossier.representatives) == 4
    assert "definition" in report.dossier.missing_sections
    assert report == select_dossier(
        value, root_id="sense", members=tuple(reversed(members)), member_budget=4
    )
    with pytest.raises(ValueError, match="independent assessment"):
        DossierMember.model_validate(
            {**members[0].model_dump(), "qualification": "independently_supported"}
        )


def test_automatic_comparison_run_and_released_report_roundtrip():
    from corpus_structure.core.method import UnitRef
    from corpus_structure.core.vocab import TaskUnitType
    from corpus_structure.semantic.characterization import select_primary_layers
    from corpus_structure.semantic.retained_contributions import RetainedContributionRef
    from corpus_structure.semantic.structural_products import StructuralProductReport
    from semantic.primary_formal_fixture import formal_layers

    value = inputs()
    primary = formal_layers(value)
    views = {}
    for source in legacy_structural_sources(value):
        passages = sorted(
            (p for p in value.passages if p.source_ref == source.identity), key=lambda p: p.start
        )
        text = [" "] * max(p.end for p in passages)
        for passage in passages:
            text[passage.start : passage.end] = passage.text
        views[source.source_view_id] = SimpleNamespace(
            ref=SimpleNamespace(
                id=source.source_view_id, projection_digest=source.projection_digest
            ),
            text="".join(text),
            pieces=tuple(
                dict(kind="native_text", item_ref=f"#/texts/{number}", start=p.start, end=p.end)
                for number, p in enumerate(passages)
            ),
        )
    references = []
    retained = {}
    for passage, source, digit in zip(
        value.passages, legacy_structural_sources(value), "ab", strict=True
    ):
        key = "source-contribution:" + digit * 64
        references.append(
            RetainedContributionRef(
                contribution_id=key,
                project_id=source.project_id,
                run_id=source.run_id,
                cut_id=source.cut_id,
                release_id=source.release_id,
                result_revision=source.result_revision,
                selected_task_id=source.native_task_id + 1,
                origin_task_id=source.native_task_id + 1,
                runtime_fingerprint="runtime",
            )
        )
        pin = dict(
            source_view_id=source.source_view_id,
            native_product_task_id=source.native_task_id,
            product_digest=source.native_content_digest,
            projection_digest=source.projection_digest,
            recipe_digest=source.recipe_digest,
        )
        retained[key] = {
            "contributions": [
                dict(
                    contribution_id=key,
                    pin=pin,
                    component=dict(
                        kind="predicate_reading",
                        question_version="6",
                        frame="frame",
                        scope=passage.passage_id,
                    ),
                ),
                dict(
                    contribution_id="frame",
                    pin=pin,
                    component=dict(
                        kind="predicate_frame",
                        scope=passage.passage_id,
                        frame_members=[
                            dict(
                                role="predicate",
                                contribution="action",
                                outcome="complete",
                                extents=[dict(start=passage.start, end=passage.end)],
                            )
                        ],
                    ),
                ),
            ]
        }
    value = value.model_copy(update={"dependencies": (*value.dependencies, *retained)})
    cfg = StructuralComparisonConfig(
        inputs=value,
        structural_input_digest=value.identity,
        characterization_layers=tuple(pin.values() for pin in primary),
        left_id="a",
        right_id="b",
        left_reading=references[0],
        right_reading=references[1],
    )
    method = StructuralComparisonMethod()
    assert method.select(None, cfg)[0].unit_key == value.identity

    def validate_inputs(actual):
        assert actual == value

    result = method.run(
        (SimpleNamespace(ref=UnitRef(TaskUnitType.RUN, unit_key="run")),),
        cfg,
        SimpleNamespace(
            check_active=lambda: None,
            reader=SimpleNamespace(
                retained_source_contribution=lambda r: retained[r.contribution_id],
                validate_structural_inputs=validate_inputs,
                primary_characterization=lambda source_view_id, **selection: select_primary_layers(
                    primary, views[source_view_id], **selection
                ),
            ),
        ),
    )[0]
    assert result.structural_product is not None
    assert result.structural_product["kind"] == "qualified_comparison"
    report = StructuralProductReport.model_validate(result.structural_product)
    assert StructuralProductReport.model_validate_json(report.model_dump_json()) == report
    assert method.version == "6"
    assert report.comparison is not None
    action = report.comparison.dimensions[1]
    assert action.outcome == "different_lexical_value"
    assert action.left_group is not None and action.left_group.members[0].lexical_value == "hello"
    assert action.right_group is not None and action.right_group.members[0].lexical_value == "world"
    assert method.select(None, StructuralComparisonConfig()) == ()
