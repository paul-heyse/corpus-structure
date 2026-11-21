"""Acquire one reference parent through an exact live selection before opening its body."""

from sqlalchemy import Text, column, func, select
from sqlalchemy.dialects.postgresql import JSONB

from .data_operation_consumers import BoundConsumerSelection
from .data_operation_json import json_loads
from .data_operation_jsonb import json_context_equal, json_context_value
from .data_operation_model import BoundRoleMember, EffectiveDataOperationModel
from .data_operation_storage import AdmittedDataRead, admitted_data_read
from .data_operation_support import support_reference_records
from .data_operation_values import decode_semantic_value
from .reference_resolution import AcquiredReferencePartition, ProducingReferenceInput


class LiveReferenceAccess:
    """Separate exact current use from the historical bindings used by the resolver."""

    def __init__(
        self,
        connection,
        model: EffectiveDataOperationModel,
        selection: BoundConsumerSelection,
        *,
        demand_id: str,
        read_id: str,
        trust_snapshot: dict,
        max_partition_bytes: int,
    ):
        if type(max_partition_bytes) is not int or max_partition_bytes <= 0:
            raise ValueError("reference reads require positive partition packet capacity")
        self.connection = connection
        self.model = model
        self.selection = selection
        self.demand_id = demand_id
        self.read_id = read_id
        self.trust_snapshot = trust_snapshot
        self.max_partition_bytes = max_partition_bytes
        self._current: tuple[BoundRoleMember, AdmittedDataRead, object] | None = None

    def authorize(self, binding: ProducingReferenceInput) -> None:
        self._current = None
        # Equality of projected replacement inputs never unlocks the original parent.
        members = tuple(
            member
            for member in self.selection.role(binding.role).members
            if (member.product, member.member, member.kind_contract)
            == (binding.product_id, binding.member_id, binding.kind_contract)
        )
        if len(members) != 1 or members[0].multiplicity != 1:
            raise PermissionError("original reference parent is outside the exact current support")
        (member,) = members
        selection = self.selection.binding
        context = selection.subject_context
        if context is None:
            raise PermissionError("live reference requires its acquired subject context")
        read = admitted_data_read(
            self.connection,
            self.demand_id,
            selection.operation,
            self.trust_snapshot,
            self.model,
            read_id=self.read_id,
            subject=context.subject,
            original_source=context.original_source,
            analyzed_scope=json_loads(context.analyzed_scope),
            selected_pins=[{"product_id": member.product, "member_id": member.member}],
        )
        expected_evidence = {read.admission_evidence} if read.accepted_kind_contracts else set()
        if set(selection.admission_evidence) != expected_evidence:
            raise PermissionError("reference selection belongs to another native read boundary")
        rows = read.relation.c
        acquired = self.connection.execute(
            select(rows.meaning_body)
            .where(
                rows.product == member.product,
                rows.member.is_not_distinct_from(member.member),
                rows.kind_contract == member.kind_contract,
                rows.subject == member.subject,
                rows.subject_definition == member.subject_definition,
                rows.original_source.is_not_distinct_from(member.original_source),
                json_context_equal(
                    rows.analyzed_scope, json_context_value(json_loads(member.analyzed_scope))
                ),
                rows.support_evidence == json_context_value(json_loads(member.support_evidence)),
                rows.support_episodes == list(member.support_episodes),
                rows.support_references == support_reference_records(member.support_references),
                rows.position.is_not_distinct_from(member.position),
                rows.multiplicity == member.multiplicity,
            )
            .limit(2)
        ).fetchall()
        if len(acquired) != 1:
            raise PermissionError("exact original reference parent is no longer available")
        self._current = member, read, acquired[0].meaning_body

    def _authorized(self, product_id: str):
        if self._current is None or self._current[0].product != product_id:
            raise PermissionError("reference body requires exact parent authorization")
        return self._current

    def product(self, product_id: str) -> object:
        pin, _, body = self._authorized(product_id)
        if pin.member is not None:
            raise PermissionError("selected member does not authorize its whole parent body")
        return decode_semantic_value(body)

    def member(self, product_id: str, member_id: str) -> object:
        pin, read, body = self._authorized(product_id)
        if pin.member == member_id:
            return decode_semantic_value(body)
        if pin.member is not None:
            raise PermissionError("selected member does not authorize another member body")
        selected = self.connection.scalar(
            select(func.ops.data_binding_reference_member(*read.binding_arguments, member_id))
        )
        if selected is None:
            raise KeyError(member_id)
        return decode_semantic_value(selected)

    def partition(
        self, product_id: str, collection: str, partition_key: str
    ) -> AcquiredReferencePartition:
        pin, read, _ = self._authorized(product_id)
        if pin.member is not None:
            raise PermissionError("selected member does not authorize its parent's partitions")
        names = {
            identity.owner
            for identity in self.model.identities
            if identity.domain == "kind" and identity.key == pin.kind_contract
        }
        declarations = tuple(
            json_loads(kind.facts).get("collections", {}).get(collection)
            for kind in self.model.kinds
            if kind.semantic_id in names and kind.category == "class"
        )
        if (
            len(declarations) != 1
            or not declarations[0]
            or declarations[0]["unit"] != "partitioned"
        ):
            raise ValueError("reference requires a declared partitioned collection")
        packets = func.ops.data_binding_partitions(
            *read.binding_arguments, self.max_partition_bytes, collection, partition_key
        ).table_valued(column("product_id", Text()), column("packet", JSONB()))
        returned = self.connection.execute(select(*packets.c).limit(2)).fetchall()
        if len(returned) != 1:
            raise KeyError((collection, partition_key))
        returned_product, packet = returned[0]
        if returned_product is None and packet is None:
            raise ValueError("reference partition exceeds owned packet capacity")
        if returned_product != product_id:
            raise PermissionError("reference partition belongs to another parent")
        return AcquiredReferencePartition(
            packet["partition_digest"], packet["body"], tuple(declarations[0]["address"])
        )
