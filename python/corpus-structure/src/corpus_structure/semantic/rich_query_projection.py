"""Deterministic named rich-query preparation and rows over acquired native inputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .data_operation_json import json_loads
from .data_operation_value_codec import decode_semantic_value
from .rich_graph_validation import RichWholeInput, read_retained_rich_graph
from .rich_knowledge_contracts import DdoRichSelectedMember
from .rich_queries import PreparedRichQueryIndex, query_rows

if TYPE_CHECKING:
    from .data_operation_model import EffectiveDataOperationModel, SubjectContext
    from .rich_queries import RichQuery, RichQueryIndex
    from .types import PreparedRelease


@dataclass(frozen=True)
class RichQueryInput:
    """An acquired whole and its immutable release/model interpretation.

    The body retains its native tagged value encoding until preparation. Validation scratch
    state is rebuilt inside the semantic workload and never supplied by acquisition.
    Prepared-release memoization is owned by that immutable release's loader.
    """

    prepared: PreparedRelease
    model: EffectiveDataOperationModel
    context: SubjectContext
    reference: bytes
    body: bytes
    decimal_fixed_point_digits: int = field(kw_only=True)


def prepare_rich_query(inputs: RichQueryInput, *, max_members: int) -> PreparedRichQueryIndex:
    reference = DdoRichSelectedMember.model_validate(json_loads(inputs.reference))
    whole = RichWholeInput(
        reference,
        decode_semantic_value(
            json_loads(inputs.body),
            decimal_fixed_point_digits=inputs.decimal_fixed_point_digits,
        ),
    )
    state = read_retained_rich_graph(
        inputs.prepared,
        inputs.model,
        context=inputs.context,
        retained=whole,
        inputs=(reference,),
        whole_inputs=(whole,),
    )
    return PreparedRichQueryIndex.build(
        state,
        max_members=max_members,
        decimal_fixed_point_digits=inputs.decimal_fixed_point_digits,
    )


def rich_query_metadata(index: RichQueryIndex) -> dict[str, list[dict[str, Any]]]:
    """Derive diagnostics from the same admitted index that produced the rows."""
    return dict(unknowns=[index.unknowns[key] for key in sorted(index.unknowns)])


def derive_rich_query_rows(
    index: RichQueryIndex, query: RichQuery, metadata: dict[str, list[dict[str, Any]]]
):
    """Project rows using only the acquired whole and typed query selection."""
    for row in query_rows(index, query):
        metadata.update(rich_query_metadata(index))
        yield dict(value=row.value, **metadata)
    metadata.update(rich_query_metadata(index))
