"""Controlled selected source members, without native publication authority."""

from corpus_structure.semantic.data_operation_consumers import SelectedConsumerValue
from corpus_structure.semantic.data_operation_model import BoundRoleMember
from corpus_structure.semantic.data_operation_ports import HydratedRoleValue
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.native_source_view import thaw_native
from corpus_structure.semantic.source_products import source_subject


def hydrated_source(source, kind_contract):
    body = source.value
    member = BoundRoleMember(
        "controlled:source-product", kind_contract, source_subject(body["source"]),
        body["source"]["document"], canonical_bytes({"source": body["source"], "selectors": body["selectors"]}),
        b"{}", (), b"{}", member="controlled:source-member",
        subject_definition="original-source-view", support_references=(),
    )
    selected = SelectedConsumerValue.acquire(
        member, source.content, canonical_bytes(semantic_value(thaw_native(body)))
    )
    return HydratedRoleValue("source", kind_contract, selected.value(), selected=selected)
