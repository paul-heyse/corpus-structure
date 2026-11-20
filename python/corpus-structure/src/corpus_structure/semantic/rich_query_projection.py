"""Deterministic named rich-query preparation and rows over acquired native inputs."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import TYPE_CHECKING

from .data_operation_json import json_bytes, json_loads
from .data_operation_values import decode_semantic_value
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


def frontier_content_witness(content: bytes) -> str | None:
    """Identify an authorized bodyless page while preserving its native envelope size.

    N34's product view adds the immutable canonical bodies to the same page
    projection used by the body-rechecking frontier view. The three varying
    receipt strings still contribute their encoded lengths to the key because
    PostgreSQL enforces the byte limit on the complete product envelope.
    """
    projection = json_loads(content)
    if projection["view"] != "frontier" or projection.get("support_page") is not None:
        return None
    for name in ("read_id", "read_snapshot", "frontier_at"):
        value = projection.get(name)
        following = projection.get("continuation")
        if not isinstance(value, str) or not value or not value.isascii():
            return None
        size = len(json_bytes(value))
        projection[name] = size
        if following is not None:
            if following.get(name) != value:
                return None
            following[name] = size
    return sha256(json_bytes(projection)).hexdigest()


def prepare_rich_query(inputs: RichQueryInput, *, max_members: int):
    reference = DdoRichSelectedMember.model_validate(json_loads(inputs.reference))
    whole = RichWholeInput(reference, decode_semantic_value(json_loads(inputs.body)))
    state = read_retained_rich_graph(
        inputs.prepared,
        inputs.model,
        context=inputs.context,
        retained=whole,
        inputs=(reference,),
        whole_inputs=(whole,),
    )
    return PreparedRichQueryIndex.build(state, max_members=max_members)


def rich_query_metadata(index: RichQueryIndex) -> dict:
    """Derive diagnostics from the same admitted index that produced the rows."""
    return dict(unknowns=[index.unknowns[key] for key in sorted(index.unknowns)])


def derive_rich_query_rows(index: RichQueryIndex, query: RichQuery):
    """Project rows using only the acquired whole and typed query selection."""
    for row in query_rows(index, query):
        yield dict(value=row.value, **rich_query_metadata(index))
