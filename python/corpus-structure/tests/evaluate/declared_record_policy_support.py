"""Controlled protected grade inputs; no native admission or judgment authority."""

from corpus_structure.evaluate.declared_record_policy import (
    DdoRecordCoverage, DdoRecordFinalEvent, DdoRecordGrade, DdoRecordGradeEvent, DdoRecordGradeFrame,
    DdoRecordOrigin, DdoRecordReferencePass,
)
from corpus_structure.semantic.declared_structural_references import DeclaredProductRef, DeclaredStructuralSource
from semantic.record_policy_support import vector

def source(index):
    return DeclaredStructuralSource(
        source=f'["source:{index}",null]', source_product=f"source:{index}",
        subject=f"subject:{index}", subject_definition="subject-definition:original-section",
        document=f"original:{index}", original_source=f"original:{index}",
        projection_digest="a" * 64, section_pointer="#/groups/0", membership="descendants",
        project_id="project:one", analyzed_scope_meaning='["null"]', kind_contract="kind:source",
    )


def address(selected, product):
    return DeclaredProductRef(
        product_id=product, member_id=None, kind_contract="kind:reading",
        project_id=selected.project_id, subject=selected.subject,
        subject_definition=selected.subject_definition, original_source=selected.original_source,
        analyzed_scope_meaning=selected.analyzed_scope_meaning,
    )


def grade_frame(*, calibration=False):
    first, empty = source(1), source(2)
    reading = address(first, "product:reading")
    passes = tuple(DdoRecordReferencePass(
        reference=address(first, "reference:" + kind), source=first, pass_kind=kind, author="author:" + kind,
        content_digest=content * 64, question_digest="e" * 64, rubric_digest="f" * 64,
        source_cut_id="cut:source", adjudicates=("b" * 64, "c" * 64) if kind == "C" else (),
    ) for kind, content in (("A", "b"), ("B", "c"), ("C", "d")))
    event = DdoRecordGradeEvent(
        record_id="record:0", interpretation_id="reading:0", reading=reading,
        source=first, source_release_id="release:test", derivation_id="derivation:reading",
        reading_recipe="resolve.m1_readings/declared", features=vector(0, -3), correct=False,
        origin_group="origin:one", final_event=DdoRecordFinalEvent(
            feature_instance_digest="1" * 64, feature_input_digest="a" * 64,
            event_procedure="procedure:whole-reading", final_event_score=-123.5,
        ) if calibration else None,
    )
    passes = (*passes, *(row.model_copy(update={"source": empty, "question_digest": "0" * 64}) for row in passes))
    return DdoRecordGradeFrame(
        partition="final_event_calibration" if calibration else "feature_fit",
        project_id="project:one", family="table", family_contract="kind:table-reading",
        reading_recipe="resolve.m1_readings/declared", subset="source-sections",
        question_digest="e" * 64, rubric_digest="f" * 64, reference_digest="d" * 64,
        source_cut_id="cut:source", prediction_cut_id="cut:prediction",
        source_release_id="release:original", prediction_release_id="release:test",
        sources=(first, empty), reference_passes=passes, events=(event,),
        coverage=(DdoRecordCoverage(source=first, outputs=(reading,), outcome="completed", event_ids=("reading:0",)),
                  DdoRecordCoverage(source=empty, outputs=(), outcome="no_output", event_ids=())),
        origin_groups=(DdoRecordOrigin(source=first, origin_group="origin:one"),
                       DdoRecordOrigin(source=empty, origin_group="origin:two")),
    )




def validate_frame_changes(frame, **changes):
    return DdoRecordGradeFrame.model_validate({**frame.model_dump(mode="python"), **changes})


def training_grade(*, calibration=False, feature=None, held_out_from=()):
    from corpus_structure.semantic.record_policy import reading_potential
    base = grade_frame()
    if calibration:
        assert feature is not None
    sources = tuple(source(index + (100 if calibration else 0)) for index in range(6))
    events, coverage, origins = [], [], []
    for index, (selected, value) in enumerate(zip(sources, (-3., -2., -1., 1., 2., 3.), strict=True)):
        reading = address(selected, f"product:{selected.original_source}")
        features = vector(index + (100 if calibration else 0), value)
        if calibration:
            features = features.model_copy(update={"release_id": "release:compatible"})
        final_event = None
        if calibration:
            assert feature is not None
            final_event = DdoRecordFinalEvent(
                feature_instance_digest=feature.digest, feature_input_digest=features.input_digest,
                event_procedure="procedure:whole-reading",
                final_event_score=reading_potential(feature.parameters, tuple(value for value in features.values if value is not None)),
            )
        event = DdoRecordGradeEvent(
            record_id=features.record_id, interpretation_id=features.interpretation_id,
            reading=reading, source=selected, source_release_id=features.release_id,
            derivation_id=f"derivation:{index}", reading_recipe=base.reading_recipe,
            features=features, correct=index >= 3, origin_group=f"origin:{selected.original_source}",
            final_event=final_event,
        )
        events.append(event)
        coverage.append(DdoRecordCoverage(source=selected, outputs=(reading,), outcome="completed", event_ids=(features.interpretation_id,)))
        origins.append(DdoRecordOrigin(source=selected, origin_group=event.origin_group))
    if calibration:
        a, b, c = base.reference_passes[:3]
        passes = (a.model_copy(update={"content_digest": "1" * 64}),
                  b.model_copy(update={"content_digest": "2" * 64}),
                  c.model_copy(update={"content_digest": "3" * 64, "adjudicates": ("1" * 64, "2" * 64)}))
    else:
        passes = base.reference_passes[:3]
    passes = tuple(row.model_copy(update={"source": selected, "question_digest": f"{index+1:064x}"})
                   for index, selected in enumerate(sources) for row in passes)
    return DdoRecordGrade.from_frame(validate_frame_changes(
        base, sources=sources, events=tuple(events), coverage=tuple(coverage), origin_groups=tuple(origins),
        partition="final_event_calibration" if calibration else "feature_fit",
        prediction_release_id="release:compatible" if calibration else "release:test",
        reference_passes=passes, reference_digest=("3" if calibration else "d") * 64,
        held_out_from=held_out_from,
    ))


