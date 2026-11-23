"""Acquire one reference parent through an exact live selection before opening its body."""

from dataclasses import replace
from itertools import batched
from typing import Any, Literal, overload

import pyarrow as pa
from sqlalchemy import Text, bindparam, column, func, select
from sqlalchemy.dialects.postgresql import JSONB

from .data_operation_consumers import BoundConsumerSelection
from .data_operation_json import json_loads, native_json_loads
from .data_operation_jsonb import json_context_equal, json_context_value
from .data_operation_model import BoundRoleMember, EffectiveDataOperationModel
from .data_operation_storage import AdmittedDataRead, admitted_data_read
from .data_operation_support import support_reference_records
from .data_operation_values import decode_semantic_value
from .data_product_reference import ReferenceKey
from .reference_resolution import (
    ProducingReferenceBindings,
    ProducingReferenceInput,
    ReferenceResolver,
    ReferenceTarget,
)
from .selected_graph_budget import SelectedGraphBudgetExceeded

_NAVIGATION_MEMBERS = pa.schema(
    [
        pa.field("ordinal", pa.int64(), nullable=False),
        pa.field("use_id", pa.string(), nullable=False),
        pa.field("input_role", pa.string(), nullable=False),
        pa.field("occurrence", pa.string()),
        pa.field("product_id", pa.string(), nullable=False),
        pa.field("target_member_id", pa.string(), nullable=False),
        pa.field("multiplicity", pa.int64(), nullable=False),
    ]
)
_NAVIGATION_RESULTS = _NAVIGATION_MEMBERS.append(
    pa.field("target_kind_contract", pa.string(), nullable=False)
)


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
            raise ValueError("reference reads require positive item capacity")
        self.connection = connection
        self.model = model
        self.selection = selection
        self.demand_id = demand_id
        self.read_id = read_id
        self.trust_snapshot = trust_snapshot
        self.max_partition_bytes = max_partition_bytes
        self._current: tuple[BoundRoleMember, AdmittedDataRead] | None = None

    def _read(self, member: BoundRoleMember, *, metadata_only: bool) -> AdmittedDataRead:
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
            metadata_only=metadata_only,
        )
        expected_evidence = {read.admission_evidence} if read.accepted_kind_contracts else set()
        if set(selection.admission_evidence) != expected_evidence:
            raise PermissionError("reference selection belongs to another native read boundary")
        return read

    @staticmethod
    def _exact_member(read, member, field):
        rows = read.relation.c
        return (
            select(rows[field])
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
        )

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
        read = self._read(member, metadata_only=True)
        acquired = self.connection.execute(self._exact_member(read, member, "product")).fetchall()
        if len(acquired) != 1:
            raise PermissionError("exact original reference parent is no longer available")
        self._current = member, read

    def _body(self, pin: BoundRoleMember) -> object:
        read = self._read(pin, metadata_only=False)
        rows = self.connection.execute(self._exact_member(read, pin, "meaning_body")).fetchall()
        if len(rows) != 1:
            raise PermissionError("exact original reference body is no longer available")
        return decode_semantic_value(rows[0].meaning_body)

    def _authorized(self, product_id: str):
        if self._current is None or self._current[0].product != product_id:
            raise PermissionError("reference body requires exact parent authorization")
        return self._current

    def product(self, product_id: str) -> object:
        pin, _ = self._authorized(product_id)
        if pin.member is not None:
            raise PermissionError("selected member does not authorize its whole parent body")
        return self._body(pin)

    def member(self, product_id: str, member_id: str) -> object:
        pin, read = self._authorized(product_id)
        if pin.member == member_id:
            return self._body(pin)
        if pin.member is not None:
            raise PermissionError("selected member does not authorize another member body")
        selected = self.connection.scalar(
            select(func.ops.data_binding_reference_member(*read.binding_arguments, member_id))
        )
        if selected is None:
            raise KeyError(member_id)
        return decode_semantic_value(selected)

    def item(
        self, product_id: str, collection: str, partition_key: str, item_key: ReferenceKey
    ) -> object:
        pin, read = self._authorized(product_id)
        if pin.member is not None:
            raise PermissionError("selected member does not authorize its parent's partitions")
        items = func.ops.data_binding_reference_item(
            *read.binding_arguments,
            self.max_partition_bytes,
            collection,
            partition_key,
            bindparam("reference_item_key", list(item_key), type_=JSONB()),
        ).table_valued(column("product_id", Text()), column("canonical_text", Text()))
        returned = self.connection.execute(select(*items.c)).one_or_none()
        if returned is None:
            raise KeyError((collection, partition_key, item_key))
        returned_product, canonical_text = returned
        if returned_product != product_id:
            raise PermissionError("reference item belongs to another parent")
        if canonical_text is None:
            raise ValueError("reference item exceeds owned capacity")
        return decode_semantic_value(native_json_loads(canonical_text))


def reference_input_address(pin, *, occurrence_binding=False, occurrence_position=False):
    """The use address an original producing input must still match."""
    return (
        None if occurrence_binding or occurrence_position else pin["position"],
        pin["product_id"],
        pin.get("member_id"),
        pin["multiplicity"],
        pin.get("occurrence_label"),
    )


class SelectedNativeReferenceAccess:
    """Reference target bodies reachable through one selected output's exact inputs."""

    def __init__(self, live, selected):
        self.live = live
        self.selected = selected
        self.bound: ProducingReferenceInput | None = None

    def inputs(self, *, role, body=False, product_id=None):
        filters = {"input_role": role}
        if product_id is not None:
            filters["input_product_id"] = product_id
        return self.live.answers(
            "read_selected_derivation_facts",
            use_id=self.selected.use_id,
            derivation_id=self.selected.derivation_id,
            body=body,
            **filters,
        )

    @staticmethod
    def _matches(row, binding):
        return (
            row["role"] == binding.role
            and row["product_id"] == binding.product_id
            and row.get("member_id") == binding.member_id
            and row["kind_contract"] == binding.kind_contract
            and row["multiplicity"] == binding.multiplicity
        )

    def authorize(self, binding):
        self.bound = None
        rows = (
            row
            for row in self.inputs(role=binding.role, product_id=binding.product_id)
            if self._matches(row, binding)
        )
        if next(rows, None) is None:
            raise PermissionError("original reference parent is outside the exact selected support")
        self.bound = binding

    def _pin(self, product_id):
        if self.bound is None or self.bound.product_id != product_id:
            raise PermissionError("reference body requires exact parent authorization")
        return self.bound

    def _body(self, binding):
        rows = (
            row
            for row in self.inputs(role=binding.role, body=True, product_id=binding.product_id)
            if self._matches(row, binding)
        )
        row = next(rows, None)
        if row is None:
            raise PermissionError("exact original reference body is no longer available")
        return decode_semantic_value(row["meaning_body"])

    def _address(self, product_id, **address):
        rows = iter(
            self.live.answers(
                "read_selected_partitions",
                use_id=self.selected.use_id,
                product_id=product_id,
                **address,
            )
        )
        row = next(rows, None)
        if row is None:
            raise KeyError(tuple(address.values()))
        if next(rows, None) is not None:
            raise ValueError("reference repeats its exact target address")
        return decode_semantic_value(row["meaning_body"])

    def product(self, product_id):
        binding = self._pin(product_id)
        if binding.member_id is not None:
            raise PermissionError("selected member does not authorize its whole parent body")
        return self._body(binding)

    def member(self, product_id, member_id):
        binding = self._pin(product_id)
        if binding.member_id == member_id:
            return self._body(binding)
        if binding.member_id is not None:
            raise PermissionError("selected member does not authorize another member body")
        return self._address(product_id, member_id=member_id)

    def item(self, product_id, collection, partition_key, item_key):
        if self._pin(product_id).member_id is not None:
            raise PermissionError("selected member does not authorize its parent's partitions")
        return self._address(
            product_id, collection=collection, partition_key=partition_key, item_key=list(item_key)
        )


class PreparedSelectedOutputReferences:
    """One acquired cut/use with reusable exact target bindings and resolvers.

    Preparation is invocation-owned. Each resolution still checks its declared
    slot, unique producing occurrence and actual parent access; memoized content
    never authorizes a different current use or a different target path.
    """

    def __init__(self, scope, selected):
        from .detached_reference_resolution import IndexedReferenceAccess

        live = getattr(scope, "live", None)
        self.derivation_id = selected.derivation_id
        self.output_role = selected.output["role"]
        self.targets = {}
        self._original_roles = {}
        self.definition: dict[str, Any]
        if live is not None:
            from .data_operation_admission import bound_data_operation_model
            from .data_operation_kind_refinements import input_kind_contracts
            from .releases import open_release

            if selected.selection is None or selected.release_id is None:
                raise PermissionError("selected reference requires its disclosed producing binding")
            model = live.model
            if selected.release_id != scope.cut.record["release_id"]:
                model = bound_data_operation_model(
                    open_release(live.connection, selected.release_id)
                )
            operation = model.operation(selected.operation_id)
            roles = [role for role in operation.roles if role.direction == "input"]
            contracts = input_kind_contracts(model, (role.kind for role in roles))
            self.definition = {
                "input_roles": [
                    {
                        "name": role.name,
                        "kind": role.kind,
                        "accepted_kind_contracts": contracts[role.kind],
                    }
                    for role in roles
                ],
                "support_contract": {
                    "reference_targets": [target.record() for target in operation.reference_targets]
                },
            }
            self.index = None
            self.project_id = scope.cut.record["project_id"]
            self.selection = selected.selection
            self.access = SelectedNativeReferenceAccess(live, selected)
            return

        def row_map(relation, *fields):
            return scope.index.mapping(relation, fields)

        cut = scope.cut.record
        # An ordinary report disclosed through a protected issuer can be selected
        # by its exact support edge even when it is outside the issuer frontier.
        use = row_map("ops.demand_use", "id").get(selected.use_id)
        if (
            use is None
            or use["fate"] != "fulfilled"
            or use["derivation_id"] != selected.derivation_id
        ):
            raise ValueError("selected reference lacks its exact fulfilled producing use")
        selection = use["selection"]
        episode = row_map("ops.data_derivation", "id")[selected.derivation_id]
        definitions = row_map("sem.data_operation_definition", "release_id", "operation_id")
        definition = definitions[episode["release_id"], selected.operation_id]
        self.index = scope.index
        self.project_id = cut["project_id"]
        self.selection = selection
        self.definition = definition
        self.access = IndexedReferenceAccess(
            row_map,
            cut["project_id"],
            population_archive=getattr(scope.index, "population_archive", None),
        )

    def _inputs(self, role):
        if isinstance(self.access, SelectedNativeReferenceAccess):
            if role not in self._original_roles:
                self._original_roles[role] = tuple(self.access.inputs(role=role))
            return self._original_roles[role]
        assert self.index is not None
        return tuple(
            self.index.rows_for(
                "ops.data_derivation_input", derivation_id=self.derivation_id, role=role
            )
        )

    @staticmethod
    def _require_slot(reference, target):
        uses_occurrence = (
            target.get("occurrence_field") is not None
            or target.get("occurrence_binding", False)
            or target.get("occurrence_position", False)
        )
        if (reference.role, reference.variant, reference.collection) != (
            target["input_role"],
            target["variant"],
            target.get("collection"),
        ) or (reference.occurrence is not None) != uses_occurrence:
            raise ValueError("reference differs from its declared slot target")

    def _prepare(self, path):
        from .detached_reference_resolution import (
            reference_input_occurrence,
            reference_role_contracts,
        )

        if path in self.targets:
            return self.targets[path]
        selection, definition, access = self.selection, self.definition, self.access
        targets = tuple(
            target
            for target in definition["support_contract"].get("reference_targets", ())
            if target["output_role"] == self.output_role
            and target.get("output_collection") is None
            and target["path"] == path
        )
        if len(targets) != 1:
            raise ValueError("selected reference requires its one declared output target")
        (target,) = targets
        contracts = reference_role_contracts(definition["input_roles"], target)
        role = target["input_role"]
        occurrence_field = target.get("occurrence_field")
        occurrence_binding = target.get("occurrence_binding", False)
        occurrence_position = target.get("occurrence_position", False)
        uses_occurrence = occurrence_field is not None or occurrence_binding or occurrence_position
        current_support = {
            reference_input_address(
                pin, occurrence_binding=occurrence_binding, occurrence_position=occurrence_position
            )
            for pin in selection["inputs"]
            if pin["role"] == role
        }
        originals = self._inputs(role)
        if not uses_occurrence and len(originals) != 1:
            raise ValueError("selected reference lacks its scalar original input")
        bindings = []
        for original in originals:
            product_id, member_id = original["product_id"], original.get("member_id")
            label = original.get("occurrence_label")
            address = reference_input_address(
                original,
                occurrence_binding=occurrence_binding,
                occurrence_position=occurrence_position,
            )
            if address not in current_support:
                continue
            if isinstance(access, SelectedNativeReferenceAccess):
                bound_packet = original
            else:
                parent = access.product_header(product_id)
                if parent is None or parent["project_id"] != self.project_id:
                    continue
                bound_packet = (
                    parent if member_id is None else access.members.get((product_id, member_id))
                )
                if bound_packet is None:
                    continue
            kind_contract = bound_packet["kind_contract"]
            if kind_contract not in contracts:
                raise ValueError(
                    "selected reference differs from its declared producing input kind"
                )
            binding = ProducingReferenceInput(
                role, product_id, kind_contract, member_id, multiplicity=original["multiplicity"]
            )
            if occurrence_binding:
                binding = replace(binding, occurrence=label, occurrence_binding=True)
            elif occurrence_position:
                binding = replace(
                    binding, occurrence=str(original["position"]), occurrence_position=True
                )
            elif occurrence_field is not None:
                if not isinstance(access, SelectedNativeReferenceAccess):
                    body_field = "canonical_body" if member_id is None else "body"
                    occurrence_packet = (
                        access.products.get(product_id) if member_id is None else bound_packet
                    )
                    if occurrence_packet.get(body_field) is None:
                        continue
                binding = replace(
                    binding,
                    occurrence=reference_input_occurrence(access, binding, occurrence_field),
                    occurrence_field=occurrence_field,
                )
            bindings.append(binding)

        if originals and not bindings:
            raise ValueError("original reference parent is unavailable in the exact selected use")
        producing = ProducingReferenceBindings(self.derivation_id, tuple(bindings))
        resolver = ReferenceResolver(producing, access)
        prepared = target, producing, resolver
        self.targets[path] = prepared
        return prepared

    def require_original_inputs(self, *, path):
        """Authorize the complete original role through its declared output target.

        Uncited inputs can still determine complete-domain interpretation. They
        use the same original ledger and current selected authority as cited
        members, without manufacturing a member address or reading a body.
        """
        target, producing, _ = self._prepare(path)
        originals = self._inputs(target["input_role"])
        if len(producing.inputs) != len(originals):
            raise ValueError("original input role is incomplete in the exact selected use")
        for binding in producing.inputs:
            self.access.authorize(binding)
        return producing.inputs

    def _resolve_binding(self, reference, path):
        target, producing, resolver = self._prepare(path)
        self._require_slot(reference, target)
        binding = producing.resolve(
            reference,
            occurrence_field=target.get("occurrence_field"),
            occurrence_binding=target.get("occurrence_binding", False),
            occurrence_position=target.get("occurrence_position", False),
        )
        return target, resolver, binding

    def require_navigation_members(self, references):
        """Resolve an ordered navigation relation under this producing use's authority."""
        access = self.access
        if not isinstance(access, SelectedNativeReferenceAccess):
            for reference, path in references:
                self.resolve(reference, path=path)
            return

        # The same acquisition owns the original role facts and guarded addresses.
        # Repeat slots still resolve their own occurrence before sharing its body check.
        authorized: dict[tuple[str, str], str] = {}
        for chunk in batched(enumerate(references), 64, strict=False):
            if chunk[-1][0] >= access.live.max_records:
                raise SelectedGraphBudgetExceeded(
                    "selected navigation exceeds examined reference bound", cut=access.live.cut
                )
            bindings = [self._resolve_binding(reference, path)[2] for _, (reference, path) in chunk]
            if any(binding.member_id is not None for binding in bindings):
                # Pinned input members keep their original derivation body port.
                for _, (reference, path) in chunk:
                    self.resolve(reference, path=path)
                continue
            entries = []
            for (ordinal, (reference, _)), binding in zip(chunk, bindings, strict=True):
                member_id = reference.member_id
                if member_id is None:
                    raise ValueError("selected navigation requires its exact member")
                entries.append(
                    {
                        "ordinal": ordinal,
                        "use_id": access.selected.use_id,
                        "input_role": binding.role,
                        "occurrence": binding.occurrence,
                        "product_id": binding.product_id,
                        "target_member_id": member_id,
                        "multiplicity": binding.multiplicity,
                    }
                )
            requested = pa.RecordBatch.from_pylist(entries, schema=_NAVIGATION_MEMBERS)
            addresses = tuple(
                zip(
                    requested.column("product_id").to_pylist(),
                    requested.column("target_member_id").to_pylist(),
                    strict=True,
                )
            )
            pending = dict.fromkeys(address for address in addresses if address not in authorized)
            for row in access.live.partition_members(access.selected.use_id, pending):
                # This consumer needs resolution evidence, so only retain the verified
                # member kind after validating the exact semantic value once.
                decode_semantic_value(row["meaning_body"])
                authorized[row["product_id"], row["member_id"]] = row["kind_contract"]
            kinds = pa.array([authorized.get(address) for address in addresses], type=pa.string())
            resolved = pa.RecordBatch.from_arrays(
                [*requested.columns, kinds], schema=_NAVIGATION_RESULTS
            )
            if resolved.column("target_kind_contract").null_count:
                raise ValueError("reference does not resolve its declared target")

    def resolve(self, reference, *, path, metadata_only=False, with_binding=False):
        target, resolver, binding = self._resolve_binding(reference, path)
        access = self.access
        role = target["input_role"]
        occurrence_field = target.get("occurrence_field")
        occurrence_binding = target.get("occurrence_binding", False)
        occurrence_position = target.get("occurrence_position", False)
        if metadata_only:
            if reference.variant != "product" or binding.member_id is not None:
                raise ValueError("reference metadata requires its exact whole producing input")
            access.authorize(binding)
            return binding
        value = resolver.resolve(
            reference,
            ReferenceTarget(
                role,
                target["variant"],
                binding.kind_contract,
                target.get("collection"),
                occurrence_field,
                occurrence_binding,
                occurrence_position,
            ),
        )
        return (binding, value) if with_binding else value


@overload
def require_selected_output_reference(
    scope, selected, reference, *, path, metadata_only: Literal[True]
) -> ProducingReferenceInput: ...


@overload
def require_selected_output_reference(
    scope, selected, reference, *, path, with_binding: Literal[True]
) -> tuple[ProducingReferenceInput, object]: ...


@overload
def require_selected_output_reference(
    scope, selected, reference, *, path, metadata_only: bool = False
) -> object: ...


def require_selected_output_reference(
    scope, selected, reference, *, path, metadata_only=False, with_binding=False
):
    """Resolve a declared reference or authenticate its exact whole-product binding."""
    return PreparedSelectedOutputReferences(scope, selected).resolve(
        reference, path=path, metadata_only=metadata_only, with_binding=with_binding
    )
