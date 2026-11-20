"""Opt-in PE-S33 comparison over one exact retained whole-book demand.

Run from the repository environment, with the intended PostgreSQL route configured::

    uv run python docs/design_review/evidence/2026-11-20_udm20-live-withheld/compare_retained_book_construction.py DEMAND_ID --source-root REPOSITORY --package-source-root PACKAGE_SOURCE

This evidence runner acquires current native read bookkeeping and prepared capability
custody; it registers, claims and publishes no work and executes no provider. It
reopens original construction-binding cuts, hydrates only their selected inputs,
then releases every transaction before invoking the existing test-only comparator
on the main thread. Bounds refuse incomplete acquisition rather than sample it.
Stdout contains one summary with identities/counts, never source or product bodies.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from sqlalchemy import Connection

from corpus_structure.semantic._data_operation_wire import WireReadDemandResultRequest
from corpus_structure.semantic.data_operation_admission import (
    acquire_prepared_execution,
    bound_data_operation_model,
)
from corpus_structure.semantic.data_operation_consumers import (
    BoundConsumerSelection,
    hydrate_consumer_selection,
    resolve_prepared_factory,
)
from corpus_structure.semantic.data_operation_demands import DemandPlanner
from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
from corpus_structure.semantic.data_operation_ports import HydratedRoleValue
from corpus_structure.semantic.data_operation_service import (
    acquire_data_execution_basis,
    read_data_demand,
)
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.data_product_reference import (
    DataProductMemberReference,
    DataProductReference,
)
from corpus_structure.semantic.demand_results import CutSelection
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.original_documents import acquire_original_document_selection
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.storage_target import acquired_target
from corpus_structure.settings import Settings

ROOT = Path(__file__).resolve().parents[4]
OPERATION = "text.constructions/source-native"


class IncompleteBook(ValueError):
    """A bounded prerequisite or exact-custody check refused acquisition."""


@dataclass
class Progress:
    demand_id: str
    phase: str = "initialization"
    frontier_pages: int = 0
    frontier_bytes: int = 0
    expected_sources: int = 0
    construction_bindings: int = 0
    construction_outputs: int = 0
    input_bytes: int = 0
    binding_read_ids: set[str] = field(default_factory=set)
    target: dict[str, Any] = field(default_factory=dict)
    read_cut_id: str | None = None
    release_id: str | None = None
    runtime_id: str | None = None

    def summary(self, outcome: str) -> dict[str, Any]:
        return {
            "outcome": outcome,
            "demand_id": self.demand_id,
            "phase": self.phase,
            "target": self.target,
            "read_cut_id": self.read_cut_id,
            "release_id": self.release_id,
            "runtime_id": self.runtime_id,
            "frontier_pages": self.frontier_pages,
            "frontier_bytes": self.frontier_bytes,
            "expected_sources": self.expected_sources,
            "construction_bindings": self.construction_bindings,
            "construction_outputs": self.construction_outputs,
            "original_binding_reads": len(self.binding_read_ids),
            "input_bytes": self.input_bytes,
        }


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise IncompleteBook(code)


def _frontier(connection: Connection, args, progress: Progress):
    """Retain finite metadata from one native whole-demand cut, with no bodies."""
    first: dict[str, Any] | None = None
    continuation, cut = None, None
    retained: dict[str, dict[str, dict[str, Any]]] = {
        "uses": {},
        "obligations": {},
        "populations": {},
    }
    while True:
        _require(progress.frontier_pages < args.max_frontier_pages, "frontier-page-bound")
        page = read_data_demand(
            connection,
            args.demand,
            continuation=continuation,
            limit=args.page_rows,
            max_bytes=args.max_page_bytes,
            view="frontier",
        )
        current = CutSelection.from_native(page)
        if cut is None:
            cut, first = current, dict(page)
            progress.read_cut_id = cut.identity
        _require(current.content == cut.content, "frontier-cut-changed")
        progress.frontier_pages += 1
        progress.frontier_bytes += len(json_bytes(page))
        _require(progress.frontier_bytes <= args.max_frontier_bytes, "frontier-byte-bound")
        for name, identity, population in (
            ("uses", "use_id", page["uses"]),
            ("obligations", "obligation_id", page["obligations"]),
            ("populations", "population_id", page["populations"]),
        ):
            for item in population:
                row: dict[str, Any] = dict(item)
                previous = retained[name].get(row[identity])
                _require(previous is None or previous == row, "frontier-identity-conflict")
                retained[name][row[identity]] = row
        continuation = page["continuation"]
        if continuation is None:
            break
    assert first is not None and cut is not None
    _require(first.get("state") != "cancelled", "cancelled-demand")
    return first, retained, cut


def _expected_sources(first, rows, *, project: str, document: str, maximum: int):
    intent = first["intent"]
    edges = [
        edge
        for edge in intent["discovery"]
        if edge["target"] == OPERATION and edge.get("target_role") == "source"
    ]
    _require(len(edges) == 1, "one-construction-source-discovery-required")
    edge = edges[0]
    populations = [
        row
        for row in rows["populations"].values()
        if row["name"] == edge["population"]
        and row["evidence"]["producer_context"]["operation_id"] == edge["producer"]
        and row["evidence"]["member_role"] == edge["output_role"]
        and "selection" not in row["evidence"]
    ]
    _require(len(populations) == 1, "one-authenticated-source-population-required")
    population = populations[0]
    _require(population["complete"] is True, "source-population-not-closed")
    evidence = population["evidence"]
    producer = rows["uses"].get(evidence["admission_use_id"])
    _require(
        producer is not None
        and producer["fate"] == "fulfilled"
        and producer["derivation_id"] == evidence["derivation_id"],
        "source-population-producer-not-current",
    )
    outputs = [
        output
        for output in producer["products"]
        if output["role"] == edge["output_role"]
        and output["product_id"] == evidence["product_id"]
        and output["member_id"] is None
    ]
    _require(len(outputs) == 1, "source-population-output-mismatch")
    members = population["members"]
    _require(0 < len(members) <= maximum, "source-member-bound-or-empty")
    _require(
        all(
            member["original_source"] == document
            and member["subject_definition"] == "original-source-view"
            for member in members
        )
        and first["project_id"] == project,
        "source-population-original-context-mismatch",
    )
    expected = tuple(
        DataProductMemberReference(
            DataProductReference(evidence["product_id"]), member["member_id"]
        )
        for member in members
    )
    _require(len(set(expected)) == len(expected), "duplicate-source-members")
    return expected


def _acquire(
    connection: Connection, args, progress: Progress, *, project: str, document: str, sha256: str
):
    progress.phase = "current-whole-demand-frontier"
    first, rows, cut = _frontier(connection, args, progress)
    _require(first["project_id"] == project, "wrong-book-project")
    original = acquire_original_document_selection(
        connection, project_id=project, document_key=document
    ).reference
    _require(original.content_hash == sha256, "wrong-book-sha256")
    intent = cast(dict[str, Any], first["intent"])
    _require(intent["version"] == "data-demand-intent-v2", "full-retained-intent-required")
    references = [value["reference"] for value in intent.get("original_sources", {}).values()]
    _require(
        len(references) == 1 and references[0] == original.model_dump(mode="json"),
        "demand-original-differs-from-retained-book",
    )
    _require(
        len(intent["roots"]) == 1
        and intent["roots"][0]["original_source"] == document
        and intent["roots"][0]["analyzed_scope"]
        == {"document": document, "scope": "whole-document"},
        "whole-original-demand-root-required",
    )
    expected = _expected_sources(
        first, rows, project=project, document=document, maximum=args.max_source_members
    )
    progress.expected_sources = len(expected)
    obligations = {
        key: row for key, row in rows["obligations"].items() if row["operation_id"] == OPERATION
    }
    _require(len(obligations) == len(expected), "construction-obligation-population-mismatch")
    _require(
        all(
            row["fate"] == "fulfilled" and row["original_source"] == document
            for row in obligations.values()
        ),
        "construction-obligations-incomplete",
    )
    progress.phase = "retained-prepared-construction-capability"
    basis = acquire_data_execution_basis(
        connection, first["release_id"], first["runtime_id"], source_root=args.package_source_root
    )
    progress.release_id, progress.runtime_id = basis.key
    model = bound_data_operation_model(basis.prepared)
    admission = acquire_prepared_execution(
        connection,
        basis.prepared,
        basis.sources,
        OPERATION,
        basis.runtime,
        schema=basis.schema,
        declarations=basis.declarations,
        captured_contracts=basis.captured_contracts,
    )
    factory = resolve_prepared_factory(model, basis.prepared_sources, OPERATION)
    port = factory(
        basis.prepared,
        model,
        OPERATION,
        identity=admission.identity,
        authorize=admission.authorize,
        custody=admission.custody,
        sources=basis.prepared_sources,
    )
    declarations = {role.name: role for role in model.operation(OPERATION).roles}
    identities = {(item.owner, item.domain): item.key for item in model.identities}
    storage, acquired = DataOperationStorage(connection), []
    uses_by_obligation = defaultdict(list)
    for use in rows["uses"].values():
        if use["obligation_id"] in obligations:
            uses_by_obligation[use["obligation_id"]].append(use)
    for obligation_id, obligation in sorted(obligations.items()):
        progress.phase = "original-construction-binding"
        uses = uses_by_obligation[obligation_id]
        _require(len(uses) == 1 and uses[0]["fate"] == "fulfilled", "one-current-use-required")
        use = uses[0]
        _require(use["request_id"] == obligation["request_id"], "construction-request-mismatch")
        outputs = [output for output in use["products"] if output["role"] == "result"]
        _require(
            len(outputs) == 1
            and outputs[0]["member_id"] is None
            and outputs[0]["kind_contract"] == identities[declarations["result"].kind, "kind"],
            "one-current-construction-output-required",
        )
        progress.construction_outputs += 1
        binding_read = use["selection"]["read_id"]
        progress.binding_read_ids.add(binding_read)
        snapshot = storage.read_demand_result(
            cast(
                WireReadDemandResultRequest,
                {
                    "demand_id": args.demand,
                    "read_id": binding_read,
                    "obligation_id": obligation_id,
                    "limit": 1,
                    "max_bytes": args.max_page_bytes,
                },
            )
        )
        _require(
            len(snapshot["obligations"]) == 1
            and snapshot["obligations"][0]["obligation_id"] == obligation_id,
            "original-binding-obligation-mismatch",
        )
        candidates = tuple(
            DemandPlanner(model, storage).bound_requests(
                snapshot, authorization=b"{}", retained=True
            )
        )
        _require(len(candidates) == 1, "one-original-binding-required")
        bound = candidates[0]
        _require(
            bound.request_id == use["request_id"]
            and canonical_bytes(json_loads(bound.binding)) == canonical_bytes(use["selection"]),
            "original-binding-changed",
        )
        pins = json_loads(bound.resolved.trust_evidence)
        progress.phase = "exact-formal-sentence-hydration"
        selected = hydrate_consumer_selection(
            connection,
            model,
            BoundConsumerSelection.from_binding(bound.binding_result, operation=OPERATION),
            demand_id=pins["demand_id"],
            read_id=pins["read_id"],
            trust_snapshot=pins["trust"],
            max_bytes=args.max_packet_bytes,
        )
        progress.input_bytes += selected.measured_bytes
        _require(progress.input_bytes <= args.max_input_bytes, "total-hydrated-input-byte-bound")
        values = []
        for name, members in selected.values:
            role = declarations[name]
            decoded = tuple(member.value() for member in members)
            if role.collection == "scalar":
                _require(len(decoded) == 1, "construction-scalar-cardinality")
                value = decoded[0]
            else:
                value = decoded
            values.append(HydratedRoleValue(name, identities[role.kind, "kind"], value))
        acquired.append((port, tuple(values), bound.binding_result))
        progress.construction_bindings += 1
    _require(
        CutSelection.from_native(first).content == cut.content, "acquired-frontier-cut-changed"
    )
    return original, expected, tuple(acquired)


def _positive(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("demand", help="Exact already-retained whole-book demand ID.")
    parser.add_argument(
        "--source-root", type=Path, default=ROOT,
        help="Repository root containing the maintained comparator tests.",
    )
    parser.add_argument(
        "--package-source-root", type=Path, default=ROOT / "python/corpus-structure/src",
        help="Explicit executable package source location.",
    )
    parser.add_argument("--page-rows", type=_positive, default=128)
    parser.add_argument("--max-frontier-pages", type=_positive, default=2048)
    parser.add_argument("--max-page-bytes", type=_positive, default=16 * 1024**2)
    parser.add_argument("--max-frontier-bytes", type=_positive, default=512 * 1024**2)
    parser.add_argument("--max-source-members", type=_positive, default=4096)
    parser.add_argument("--max-packet-bytes", type=_positive, default=64 * 1024**2)
    parser.add_argument("--max-input-bytes", type=_positive, default=512 * 1024**2)
    args = parser.parse_args()
    progress = Progress(args.demand)
    try:
        _require(args.demand.startswith("demand:"), "exact-demand-id-required")
        _require(args.page_rows <= 1000, "native-page-row-bound")
        test_root = args.source_root.resolve() / "python/corpus-structure/tests"
        _require(test_root.is_dir(), "repository-source-root-required")
        # The only test import is the already maintained PE-S33 comparison owner.
        sys.path.insert(0, str(test_root))
        from semantic.prose_book_comparator import (
            BOOK_DOCUMENT,
            BOOK_PROJECT,
            BOOK_SHA256,
            compare_whole_book_construction,
        )

        with (
            open_runtime_engine(
                Settings(), "pe-s33-retained-book-comparison", purpose="write", max_size=1
            ) as engine,
            engine.begin() as connection,
        ):
            progress.target = acquired_target(connection, purpose="write").model_dump(mode="json")
            original, expected, acquired = _acquire(
                connection,
                args,
                progress,
                project=BOOK_PROJECT,
                document=BOOK_DOCUMENT,
                sha256=BOOK_SHA256,
            )
        # No connection/pool/transaction survives into either parser execution.
        progress.phase = "all-real-construction-regions"
        result = compare_whole_book_construction(
            original, expected_sources=expected, acquired=acquired
        )
        report = progress.summary("passed")
        report.update(
            regions=len(result["regions"]),
            region_outcomes={
                outcome: sum(row["outcome"] == outcome for row in result["regions"])
                for outcome in sorted({row["outcome"] for row in result["regions"]})
            },
        )
    except (Exception, KeyboardInterrupt) as error:
        report = progress.summary(
            "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
        )
        report["error_type"] = type(error).__name__
        if isinstance(error, IncompleteBook):
            report["refusal"] = str(error)  # Only fixed diagnostic codes from this script.
        print(json.dumps(report, sort_keys=True))
        return 130 if isinstance(error, KeyboardInterrupt) else 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
