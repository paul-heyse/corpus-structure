"""Send actual fixture reports through the ordinary released source-batch boundary."""

from corpus_structure.core.method import UnitRef, UnitResult
from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
from corpus_structure.semantic.observations import bind_result
from semantic.primary_formal_fixture import release


def released_report(report, *, method, version):
    bound = bind_result(
        release(),
        source="independent-structural-fixture",
        method=method,
        operation_version=version,
        configuration_hash="fixture-configuration",
        input_hash="fixture-input",
        invocation_key="fixture-invocation",
        result=UnitResult(
            ref=UnitRef(TaskUnitType.RUN, unit_key=report.product_id),
            outcome=ObservationOutcome.PRODUCED,
            structural_product=report.model_dump(mode="json"),
        ),
    )
    return bound.model_dump(mode="json")["structural_product"]
