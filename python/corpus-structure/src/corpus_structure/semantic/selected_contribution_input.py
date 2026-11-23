"""Typed selected support inputs and deterministic native-record interpretation."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from itertools import batched
from typing import TYPE_CHECKING, Any

from .authority_leaf import NativeAuthorityLeaf
from .data_operation_json import json_bytes
from .data_operation_model import SubjectContext
from .data_operation_support import ComputationalSupportReference, read_support_references
from .data_operation_value_codec import decode_semantic_value
from .refusal_types import ReadLimit, RichQueryRefused
from .rich_graph_validation import (
    RichGraphState,
    RichWholeInput,
    read_retained_rich_graph,
    read_rich_graph,
)
from .rich_knowledge_contracts import (
    DdoRichAdmission,
    DdoRichConsolidation,
    DdoRichSelectedMember,
    rich_reference_key,
)
from .selected_graph_budget import SelectedGraphBudgetExceeded

if TYPE_CHECKING:
    from ._data_operation_wire import WireDemandReadScope
    from .acquired_selected_relations import AcquiredSelectedRelations
    from .data_operation_model import EffectiveDataOperationModel
    from .demand_results import CutSelection
    from .types import PreparedRelease

RICH_NAMESPACE = "https://corpus-structure.dev/semantic/data-operation-rich-knowledge/"


@dataclass(frozen=True)
class SelectedContribution:
    reference: DdoRichSelectedMember
    context: SubjectContext
    body: Any
    nominal: str
    operation_id: str
    use_id: str
    derivation_id: str
    output: dict[str, Any]
    selection: dict | None = field(default=None, kw_only=True)
    release_id: str | None = field(default=None, kw_only=True)


@dataclass
class LiveContributionRead:
    """Invocation-owned native answers over one exact authorized cut."""

    connection: Any
    model: Any
    cut: Any
    scope: Any
    max_bytes: int
    max_records: int
    retained_bytes: int = 0
    retained_records: int = 0

    def answers(self, program, **filters):
        from .demand_results import read_selected_answer

        after = None
        while True:
            try:
                answer = read_selected_answer(
                    self.connection,
                    program,
                    self.cut.record["demand_id"],
                    project_id=self.cut.record["project_id"],
                    read_id=self.cut.record["read_id"],
                    scope=self.scope,
                    after=after,
                    max_bytes=self.max_bytes,
                    **filters,
                )
            except ReadLimit as error:
                raise SelectedGraphBudgetExceeded(str(error), cut=self.cut) from error
            self._require_answer_cut(answer)
            for row in answer["rows"]:
                self._retain_answer(row)
                yield row
            following = answer["answer_after"]
            if following is None:
                return
            if following == after:
                raise ValueError("selected answer continuation did not advance")
            after = following

    def _require_answer_cut(self, answer):
        from .demand_results import CutSelection

        if CutSelection.from_native(answer["cut"]).content != self.cut.content:
            raise ValueError("selected answer differs from its exact acquired cut")

    def _retain_answer(self, row):
        self.retained_bytes += len(json_bytes(row))
        self.retained_records += 1
        if self.retained_bytes > self.max_bytes or self.retained_records > self.max_records:
            raise SelectedGraphBudgetExceeded(
                "selected answers exceed examined bound", cut=self.cut
            )

    def partition_members(self, use_id, addresses):
        """Read exact guarded member replies in bounded groups within this cut."""
        from .data_operation_storage import DataOperationStorage
        from .demand_results import require_selected_answer_capacity
        from .ordered_native_answers import read_ordered_native_answers

        program = "read_selected_partitions"
        storage = DataOperationStorage(self.connection)
        basis = {
            "demand_id": self.cut.record["demand_id"],
            "project_id": self.cut.record["project_id"],
            "read_id": self.cut.record["read_id"],
            "use_id": use_id,
            "scope": dict(self.scope or {}),
            "max_bytes": self.max_bytes,
            "limit": 1,
        }
        # JSONB text has spaces in addition to the native canonical envelope.
        # Limit both the largest transfer and the number of simultaneously staged replies.
        max_wire_bytes = 2 * self.max_bytes
        call_bound = min(16, max(1, (64 * 1024**2) // max_wire_bytes))

        def acquire(requests):
            replies = read_ordered_native_answers(
                self.connection, program, requests, max_wire_bytes=max_wire_bytes
            )
            if replies is not None:
                yield from zip(requests, replies, strict=True)
            elif len(requests) == 1:
                yield requests[0], storage._invoke(program, requests[0])
            else:
                middle = len(requests) // 2
                yield from acquire(requests[:middle])
                yield from acquire(requests[middle:])

        for chunk in batched(addresses, call_bound, strict=False):
            requests = tuple(
                dict(basis, product_id=product_id, member_id=member_id)
                for product_id, member_id in chunk
            )
            for request, answer in acquire(requests):
                self._require_answer_cut(answer)
                try:
                    require_selected_answer_capacity(answer)
                except ReadLimit as error:
                    raise SelectedGraphBudgetExceeded(str(error), cut=self.cut) from error
                if answer["answer_after"] is not None:
                    raise ValueError("reference repeats its exact target address")
                if len(answer["rows"]) != 1:
                    raise ValueError("reference does not resolve its declared target")
                (row,) = answer["rows"]
                if (row["product_id"], row["member_id"]) != (
                    request["product_id"],
                    request["member_id"],
                ):
                    raise PermissionError("reference body differs from its exact member address")
                self._retain_answer(row)
                yield row


@dataclass(frozen=True)
class SelectedContributionScope:
    cut: CutSelection
    index: AcquiredSelectedRelations | LiveContributionRead
    prepared: PreparedRelease
    model: EffectiveDataOperationModel
    scope: WireDemandReadScope
    max_support_edges: int
    decimal_fixed_point_digits: int = field(kw_only=True)
    live: LiveContributionRead | None = field(default=None, kw_only=True)

    def products(self, *, product_id: str | None = None) -> Iterator[SelectedContribution]:
        live = getattr(self, "live", None)
        if live is not None:
            filters = {} if product_id is None else {"product_id": product_id}
            for row in live.answers(
                "read_selected_outputs", body=True, include_binding=True, **filters
            ):
                context = SubjectContext(
                    self.cut.record["project_id"],
                    row["subject"],
                    row["original_source"],
                    json_bytes(row["analyzed_scope"]),
                    subject_definition=row["subject_definition"],
                )
                reference = DdoRichSelectedMember(
                    product_id=row["product_id"],
                    member_id=row["member_id"],
                    kind_contract=row["kind_contract"],
                    support_references=(
                        ComputationalSupportReference(
                            derivation_id=row["derivation_id"], admission_use_id=row["use_id"]
                        ),
                    ),
                )
                yield SelectedContribution(
                    reference,
                    context,
                    decode_semantic_value(
                        row["meaning_body"],
                        decimal_fixed_point_digits=self.decimal_fixed_point_digits,
                    ),
                    row["kind"],
                    row["operation_id"],
                    row["use_id"],
                    row["derivation_id"],
                    {
                        "role": row["role"],
                        "position": row["position"],
                        "product_id": row["product_id"],
                        "member_id": row["output_member_id"],
                        "multiplicity": row["multiplicity"],
                    },
                    selection=row["selection"],
                    release_id=row["release_id"],
                )
            return
        index = self.index
        if isinstance(index, LiveContributionRead):
            raise ValueError("detached contribution scope requires its acquired index")
        products = index.mapping("kb.data_product", ("id",))
        members = index.mapping("kb.data_product_member", ("product_id", "member_id"))
        episodes = index.mapping("ops.data_derivation", ("id",))
        requests = index.mapping("ops.data_request", ("id",))
        kinds = index.mapping("sem.data_kind_contract", ("kind_contract",))
        authorities = {
            (leaf.derivation_id, leaf.use_id)
            for row in index.rows("ops.data_authority_leaf")
            for leaf in (NativeAuthorityLeaf.model_validate(row),)
        }
        for use in index.frontier_rows("uses"):
            if use["fate"] != "fulfilled" or use["derivation_id"] is None:
                continue
            if (use["derivation_id"], use["use_id"]) in authorities:
                # Native disclosure deliberately withholds the issuer's private
                # episode. Its conclusion has a dedicated authority-leaf reader.
                continue
            episode = episodes[use["derivation_id"]]
            request = requests[episode["request_id"]]
            for output in index.rows_for("ops.data_derivation_output", derivation_id=episode["id"]):
                if product_id is not None and output["product_id"] != product_id:
                    continue
                product = products[output["product_id"]]
                if product["project_id"] != self.cut.record["project_id"]:
                    raise ValueError(
                        "selected contribution product belongs to another native project"
                    )
                value = (
                    product
                    if output["member_id"] is None
                    else members[product["id"], output["member_id"]]
                )
                context = SubjectContext(
                    product["project_id"],
                    value["subject"],
                    value["original_source"],
                    json_bytes(value["analyzed_scope"]),
                    subject_definition=value["subject_definition"],
                )
                reference = DdoRichSelectedMember(
                    product_id=product["id"],
                    member_id=output["member_id"],
                    kind_contract=value["kind_contract"],
                    support_references=(
                        ComputationalSupportReference(
                            derivation_id=episode["id"], admission_use_id=use["use_id"]
                        ),
                    ),
                )
                yield SelectedContribution(
                    reference,
                    context,
                    decode_semantic_value(
                        product["canonical_body"] if output["member_id"] is None else value["body"],
                        decimal_fixed_point_digits=self.decimal_fixed_point_digits,
                    ),
                    kinds[value["kind_contract"]]["kind"],
                    request["operation_id"],
                    use["use_id"],
                    episode["id"],
                    output,
                )

    def graph(self, selected: SelectedContribution) -> RichGraphState:
        if selected.nominal == RICH_NAMESPACE + "DdoRichAdmission":
            root = RichWholeInput(
                selected.reference, DdoRichAdmission.model_validate(selected.body)
            )
            return read_retained_rich_graph(
                self.prepared,
                self.model,
                context=selected.context,
                retained=root,
                inputs=(selected.reference,),
                whole_inputs=(root,),
            )
        if selected.nominal != RICH_NAMESPACE + "DdoRichConsolidation":
            raise ValueError("selected contribution is not a declared rich graph whole")
        body = DdoRichConsolidation.model_validate(selected.body)
        live = getattr(self, "live", None)
        if live is not None:
            references, wholes, retained = self._live_graph_inputs(selected)
        else:
            index = self.index
            if isinstance(index, LiveContributionRead):
                raise ValueError("detached graph requires its acquired index")
            references, wholes = actual_graph_inputs(
                index,
                selected.derivation_id,
                use_id=selected.use_id,
                cut=self.cut,
                max_support_edges=self.max_support_edges,
                decimal_fixed_point_digits=self.decimal_fixed_point_digits,
            )
            kinds = index.mapping("sem.data_kind_contract", ("kind_contract",))
            retained = tuple(
                item
                for item in wholes
                if kinds[item.reference.kind_contract]["kind"]
                == RICH_NAMESPACE + "DdoRichAdmission"
            )
        return read_rich_graph(
            self.prepared,
            self.model,
            context=selected.context,
            graph=body,
            inputs=references,
            whole_inputs=wholes,
            retained_graphs=retained,
        )

    def _live_graph_inputs(self, selected):
        live = self.live
        if live is None:
            raise ValueError("native graph inputs require their acquired read")
        references, wholes, retained = {}, {}, {}
        for ordinal, row in enumerate(
            live.answers(
                "read_selected_derivation_facts",
                use_id=selected.use_id,
                derivation_id=selected.derivation_id,
                body=True,
            )
        ):
            if ordinal >= self.max_support_edges:
                raise SelectedGraphBudgetExceeded(
                    "selected inputs exceed examined-edge bound", cut=self.cut
                )
            reference = DdoRichSelectedMember(
                product_id=row["product_id"],
                member_id=row["member_id"],
                kind_contract=row["kind_contract"],
                support_references=read_support_references(row["support"]),
            )
            key = rich_reference_key(reference)
            references[key] = reference
            if reference.member_id is None:
                whole = RichWholeInput(
                    reference,
                    decode_semantic_value(
                        row["meaning_body"],
                        decimal_fixed_point_digits=self.decimal_fixed_point_digits,
                    ),
                )
                wholes[key] = whole
                if row["kind"] == RICH_NAMESPACE + "DdoRichAdmission":
                    retained[key] = whole
        return (
            tuple(references[key] for key in sorted(references)),
            tuple(wholes[key] for key in sorted(wholes)),
            tuple(retained[key] for key in sorted(retained)),
        )


def selected_use_selection(index: AcquiredSelectedRelations, use_id: str, derivation_id: str):
    """Read the exact consumed use, including value-substituted support."""
    use = index.frontier_row("uses", use_id)
    if use is None or use["fate"] != "fulfilled":
        raise ValueError("selected input support requires an exact fulfilled use")
    if use["derivation_id"] != derivation_id:
        raise ValueError("selected input support use belongs to another derivation")
    return use["selection"]


def actual_graph_inputs(
    index: AcquiredSelectedRelations,
    derivation_id: str,
    *,
    use_id: str,
    cut: CutSelection,
    max_support_edges: int,
    decimal_fixed_point_digits: int,
):
    """Resolve frozen role support by actual native output/original edges, once.

    Unpositioned bag support is a population. Index its real product/member edges
    rather than assigning all references to each value or rescanning every output.
    """
    products = index.mapping("kb.data_product", ("id",))
    members = index.mapping("kb.data_product_member", ("product_id", "member_id"))
    originals = index.mapping("ops.original_source_admission", ("id",))
    kinds = index.mapping("sem.data_kind_contract", ("kind_contract",))
    binding = selected_use_selection(index, use_id, derivation_id)
    selected_groups = defaultdict(dict)
    for selected in binding["inputs"]:
        group = (selected["role"], selected.get("position"))
        selected_groups[group][selected["product_id"], selected.get("member_id")] = selected
    support_groups = defaultdict(dict)
    for support in binding["support"]:
        group = support["role"], support.get("position")
        support_groups[group][json_bytes(support)] = support
    authorities = defaultdict(list)
    for row in index.rows("ops.data_authority_leaf"):
        leaf = NativeAuthorityLeaf.model_validate(row)
        authorities[leaf.derivation_id].append(leaf)
    references, wholes, output_cache = {}, {}, {}
    examined = 0

    def spend():
        nonlocal examined
        examined += 1
        if examined > max_support_edges:
            raise SelectedGraphBudgetExceeded(
                "selected graph support matching exceeds its examined-edge bound", cut=cut
            )

    def matching_outputs(by_product, outputs):
        candidates = by_product if len(by_product) < len(outputs) else outputs
        for product_id in candidates:
            spend()
            if product_id not in by_product or product_id not in outputs:
                continue
            for member_id in by_product[product_id]:
                spend()
                if None in outputs[product_id] or member_id in outputs[product_id]:
                    yield product_id, member_id

    for group, selections in selected_groups.items():
        by_product = defaultdict(set)
        for product_id, member_id in selections:
            by_product[product_id].add(member_id)
        supported = defaultdict(list)
        for support in support_groups[group].values():
            spend()
            kind = support["kind"]
            if kind == "computation":
                producer = support["derivation_id"]
                leaves = authorities.get(producer, ())
                if leaves:
                    matches = []
                    candidates = []
                    relevant = False
                    for leaf in leaves:
                        spend()
                        if (leaf.product_id, None) not in selections:
                            continue
                        relevant = True
                        if (
                            support.get("admission_use_id") is not None
                            and support["admission_use_id"] != leaf.use_id
                        ):
                            continue
                        candidates.append(leaf)
                    if relevant and not candidates:
                        raise RichQueryRefused(
                            "selected graph bounded authority differs from its exact admitted use"
                        )
                    for leaf in candidates:
                        from corpus_structure.semantic.record_policy_authority import (
                            AUTHORIZATION_KIND,
                            AUTHORIZATION_OPERATION,
                            DdoRecordPolicyAuthorization,
                        )

                        product = products[leaf.product_id]
                        if (
                            leaf.standing != "valid"
                            or leaf.issuer_operation != AUTHORIZATION_OPERATION
                            or leaf.kind_contract != product["kind_contract"]
                            or kinds[leaf.kind_contract]["kind"] != AUTHORIZATION_KIND
                            or kinds[leaf.kind_contract]["universe"] != "ordinary"
                            or (
                                support.get("admission_use_id") is not None
                                and support["admission_use_id"] != leaf.use_id
                            )
                        ):
                            raise RichQueryRefused(
                                "selected graph bounded authority is unavailable or differs from its permitted whole authorization conclusion"
                            )
                        DdoRecordPolicyAuthorization.model_validate_json(
                            json_bytes(
                                decode_semantic_value(
                                    product["canonical_body"],
                                    decimal_fixed_point_digits=decimal_fixed_point_digits,
                                )
                            )
                        )
                        matches.append((leaf.product_id, None))
                    fields = ("kind", "derivation_id", "admission_use_id")
                    for endpoint in matches:
                        supported[endpoint].append(
                            {name: support[name] for name in fields if name in support}
                        )
                    continue
                if producer not in output_cache:
                    outputs = defaultdict(set)
                    for row in index.rows_for("ops.data_derivation_output", derivation_id=producer):
                        spend()
                        outputs[row["product_id"]].add(row["member_id"])
                    output_cache[producer] = outputs
                outputs = output_cache[producer]
                matches = matching_outputs(by_product, outputs)
                fields = ("kind", "derivation_id", "admission_use_id")
            elif kind in {"original-source", "authored"}:
                admission = originals[support["admission_id"]]
                product_id = admission["product_id"]
                matches = (
                    ((product_id, None),)
                    if (product_id, None) in selections
                    and admission["source_reference"] == support["source_reference"]
                    else ()
                )
                fields = ("kind", "admission_id", "source_reference")
            else:
                raise ValueError("selected graph support has no current declared origin")
            for endpoint in matches:
                supported[endpoint].append(
                    {name: support[name] for name in fields if name in support}
                )
        for product_id, member_id in selections:
            product = products[product_id]
            value = product if member_id is None else members[product_id, member_id]
            reference = DdoRichSelectedMember(
                product_id=product_id,
                member_id=member_id,
                kind_contract=value["kind_contract"],
                support_references=read_support_references(supported[product_id, member_id]),
            )
            key = rich_reference_key(reference)
            references[key] = reference
            if member_id is None:
                wholes[key] = RichWholeInput(
                    reference,
                    decode_semantic_value(
                        product["canonical_body"],
                        decimal_fixed_point_digits=decimal_fixed_point_digits,
                    ),
                )
    return tuple(references[key] for key in sorted(references)), tuple(
        wholes[key] for key in sorted(wholes)
    )
