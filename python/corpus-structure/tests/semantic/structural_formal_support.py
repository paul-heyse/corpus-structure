"""Actual formal products over the current literal structural source fixtures."""

from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.formal_products import FormalEvidenceOptions
from corpus_structure.semantic.formal_readings import FormalSourceReadings
from corpus_structure.semantic.identity import canonical_bytes
from semantic.formal_products_support import released_profile
from semantic.structural_products_support import native_source


def formal_reading_sets(inputs):
    profile = released_profile()
    readings = {}
    for source in inputs.sources:
        native = native_source(profile.prepared, inputs, source)
        context = SubjectContext(
            source.project_id, source.subject, source.original_source,
            canonical_bytes(dict(source=native.value["source"], selectors=native.value["selectors"])),
            subject_definition=source.subject_definition,
        )
        product = profile.run(native, FormalEvidenceOptions(), subject_context=context)
        readings[source.identity] = FormalSourceReadings.from_products((product,), native)
    return readings
