"""Controlled protected grade inputs; no native admission or judgment authority."""

from corpus_structure.evaluate.declared_record_policy import (
    DdoRecordCoverage, DdoRecordFinalEvent, DdoRecordGradeEvent, DdoRecordGradeFrame,
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


