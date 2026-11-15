"""Current selected contribution roots and their actual native input/support proof.

The temporary selected index owns the bounded examined population. This adapter
opens no extra result, follows no latest release, and never invents a member binding.
"""

from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from corpus_structure.semantic.authority_leaf import NativeAuthorityLeaf
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.data_operation_identity import decode_semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import (
    EffectiveDataOperationModel,
    SubjectContext,
)
from corpus_structure.semantic.data_operation_read_index import SelectedRecordIndex
from corpus_structure.semantic.data_operation_support import (
    ComputationalSupportReference,
    read_support_references,
)
from corpus_structure.semantic.demand_results import (
    CutSelection,
    SelectedGraphBudgetExceeded,
    selected_record_index,
)
from corpus_structure.semantic.releases import load_release
from corpus_structure.semantic.rich_graph_validation import (
    RichWholeInput,
    read_retained_rich_graph,
    read_rich_graph,
)
from corpus_structure.semantic.rich_knowledge_contracts import (
    DdoRichAdmission,
    DdoRichConsolidation,
    DdoRichSelectedMember,
    rich_reference_key,
)
from corpus_structure.semantic.rich_queries import RichQueryRefused
from corpus_structure.semantic.types import PreparedRelease

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
    output: dict


@dataclass(frozen=True)
class SelectedContributionScope:
    cut: CutSelection
    index: SelectedRecordIndex
    prepared: PreparedRelease
    model: EffectiveDataOperationModel
    scope: dict
    max_support_edges: int

    def products(self, *, product_id=None):
        products = self.index.mapping("kb.data_product", ("id",))
        members = self.index.mapping("kb.data_product_member", ("product_id", "member_id"))
        episodes = self.index.mapping("ops.data_derivation", ("id",))
        requests = self.index.mapping("ops.data_request", ("id",))
        kinds = self.index.mapping("sem.data_kind_contract", ("kind_contract",))
        for use in self.index.frontier_rows("uses"):
            if use["fate"] != "fulfilled" or use["derivation_id"] is None:
                continue
            episode = episodes[use["derivation_id"]]
            request = requests[episode["request_id"]]
            for output in self.index.rows_for(
                "ops.data_derivation_output", derivation_id=episode["id"]
            ):
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
                        product["canonical_body"] if output["member_id"] is None else value["body"]
                    ),
                    kinds[value["kind_contract"]]["kind"],
                    request["operation_id"],
                    use["use_id"],
                    episode["id"],
                    output,
                )

    def graph(self, selected: SelectedContribution):
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
        references, wholes = actual_graph_inputs(
            self.index,
            selected.derivation_id,
            cut=self.cut,
            max_support_edges=self.max_support_edges,
        )
        kinds = self.index.mapping("sem.data_kind_contract", ("kind_contract",))
        retained = tuple(
            item
            for item in wholes
            if kinds[item.reference.kind_contract]["kind"] == RICH_NAMESPACE + "DdoRichAdmission"
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


def actual_graph_inputs(
    index: SelectedRecordIndex, derivation_id: str, *, cut: CutSelection, max_support_edges: int
):
    """Resolve frozen role support by actual native output/original edges, once.

    Unpositioned bag support is a population. Index its real product/member edges
    rather than assigning all references to each value or rescanning every output.
    """
    products = index.mapping("kb.data_product", ("id",))
    members = index.mapping("kb.data_product_member", ("product_id", "member_id"))
    episodes = index.mapping("ops.data_derivation", ("id",))
    requests = index.mapping("ops.data_request", ("id",))
    originals = index.mapping("ops.original_source_admission", ("id",))
    kinds = index.mapping("sem.data_kind_contract", ("kind_contract",))
    request = requests[episodes[derivation_id]["request_id"]]
    binding = request["binding"]
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
                            json_bytes(decode_semantic_value(product["canonical_body"]))
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
                    reference, decode_semantic_value(product["canonical_body"])
                )
    return tuple(references[key] for key in sorted(references)), tuple(
        wholes[key] for key in sorted(wholes)
    )


@contextmanager
def selected_contribution_scope(connection, request, *, product_ids=None):
    if product_ids is None:
        product_ids = None if request.product_id is None else [request.product_id]
    else:
        product_ids = sorted(set(product_ids))
        if not product_ids or (
            request.product_id is not None and product_ids != [request.product_id]
        ):
            raise ValueError("selected product roots differ from the requested product scope")
    scope = {
        name: value
        for name, value in dict(
            operation_id=request.operation_id,
            subject=request.subject,
            product_ids=product_ids,
        ).items()
        if value is not None
    }
    if "original_source" in request.model_fields_set:
        scope["original_source"] = request.original_source
    with selected_record_index(
        connection,
        request.demand_id,
        project_id=request.project_id,
        scope=scope,
        read_id=request.read_id,
        expected_cut=request.expected_cut,
        max_bytes=request.max_graph_bytes,
        max_total_bytes=request.max_graph_bytes,
        max_total_records=request.max_graph_records,
        capture_frontier=True,
    ) as (cut, index):
        prepared = load_release(connection, cut.record["release_id"])
        model = bound_data_operation_model(prepared)
        yield SelectedContributionScope(
            cut, index, prepared, model, scope, request.max_support_edges
        )
