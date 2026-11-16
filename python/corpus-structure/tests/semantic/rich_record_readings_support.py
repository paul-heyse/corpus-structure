"""Current source-reading values and independently authored inspected scopes.

Controlled pure values confer no producing-episode or native admission authority.
"""

from copy import deepcopy
from functools import cache

from evaluate.declared_record_grading_support import current_reading

from corpus_structure.semantic import prepare_release
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.rich_knowledge_sources import (
    rich_knowledge_declarations,
    rich_knowledge_schema_inputs,
)
from corpus_structure.semantic.types import ResolvedDependencies
from semantic.record_contracts_support import release_inputs


@cache
def current():
    bundle, deps = rich_knowledge_schema_inputs(
        release_inputs()[0],
        ResolvedDependencies(),
        qualification_class="StatisticsQualification",
        statement_class="SourceStatement",
    )
    return prepare_release(bundle, deps), compile_data_operations(
        bundle, declarations=rich_knowledge_declarations(deps)
    )


def inspected_reading(family):
    from corpus_structure.semantic.record_contracts import (
        anchor_identity,
        evidence_set_identity,
        interpretation_identity,
    )

    row, coordinates = current_reading(family)
    row = deepcopy(row)
    row["standing"] = "candidate"
    # This controlled producer inspected the actual selected native source scope
    # for every absent role, rather than asserting absence from missing evidence.
    anchors, sets = list(row["anchors"]), list(row["evidence_sets"])
    for field in row["fields"]:
        if field["evidence_status"] == "unavailable" and field["state"] != "present":
            anchor = dict(
                pin=row["pin"],
                space="native",
                pointer=row["pin"]["section_pointer"],
                precision="item",
            )
            anchor["anchor_id"] = anchor_identity(anchor)
            if anchor not in anchors:
                anchors.append(anchor)
            evidence = dict(
                role=field["role"],
                ordering="ordered",
                usage="context",
                anchors=(anchor["anchor_id"],),
            )
            evidence["set_id"] = evidence_set_identity(evidence)
            sets.append(evidence)
            field["evidence_sets"] = (evidence["set_id"],)
            field["evidence_status"] = "available"
    row["anchors"], row["evidence_sets"] = tuple(anchors), tuple(sets)
    row["interpretation_id"] = interpretation_identity(row)
    return row, coordinates
