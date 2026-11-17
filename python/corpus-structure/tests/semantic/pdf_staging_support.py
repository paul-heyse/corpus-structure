"""Private staged PDF build fixture shared by native consumer tests."""

import json
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
from typing import Literal, cast

import pyarrow as pa
import pytest

from corpus_structure.core.evidence import document_key
from corpus_structure.semantic._data_operation_wire import (
    WireAttemptFence,
    WireClaimDataRequestsRequest,
    WireCompletion,
    WireRequestId,
    wire_attempt_fence,
)
from corpus_structure.semantic.composed import read_data_operation_inputs
from corpus_structure.semantic.data_operation_demands import (
    DemandPlanner,
    OperationSelection,
    ReadyDataRequest,
    freeze_demand,
)
from corpus_structure.semantic.data_operation_execution_evidence import bind_execution_evidence
from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.data_operation_outcomes import successful_return_outcome
from corpus_structure.semantic.data_operation_service import execute_data_demand
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.demand_queries import DemandQueryRequest, serve_demand_query
from corpus_structure.semantic.identifiers import ProjectId, ReleaseId, RuntimeId
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.original_documents import (
    acquire_original_document_selection,
    register_original_document,
)
from corpus_structure.semantic.pdf_capture import pdf_publication_value
from corpus_structure.semantic.pdf_contracts import store_pdf_original
from corpus_structure.semantic.pdf_publication import inspect_pdf_execution_receipt
from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader, PublishedReadBudget
from corpus_structure.semantic.pdf_records import native_schema_bytes
from corpus_structure.semantic.pdf_staging import (
    begin_pdf_build,
    stage_schema,
)
from corpus_structure.semantic.product_reference import ProductReference
from semantic.current_pdf_source_support import ROOT, current_pdf_recipe
from semantic.data_operation_kernel_support import Kernel, admit_kernel

_PROJECT = "pdf-staging-controls"
type PdfFixtureCase = Literal[
    "default", "unknown-cell-coverage", "partial-cell-coverage", "integer-region-coordinates"
]

# These policies describe the controlled authored records, rather than manufacturing
# independent work with physical task IDs or a fresh nonce. The native request owns
# the inference policy as a genuine semantic determinant.
_POLICIES: dict[PdfFixtureCase, str] = {
    "default": "controlled-pdf-records-v1",
    "unknown-cell-coverage": "controlled-pdf-unknown-cell-coverage-v1",
    "partial-cell-coverage": "controlled-pdf-partial-cell-coverage-v1",
    "integer-region-coordinates": "controlled-pdf-partial-cell-integer-region-coordinates-v1",
}


@dataclass(frozen=True)
class _PdfRequest:
    ready: ReadyDataRequest
    fence: WireAttemptFence
    deadline: datetime


class _PrivatePdfBuildFactory:
    project_id = _PROJECT

    def __init__(self, kernel: Kernel, writer, admitter, original: bytes, recipe: bytes, key: str):
        self.kernel, self.writer, self.admitter = kernel, writer, admitter
        self.original, self.recipe, self.key = original, recipe, key
        self.requests: dict[str, _PdfRequest] = {}

    def __call__(self, *, case: PdfFixtureCase = "default"):
        with self.writer.begin() as conn:
            selected = acquire_original_document_selection(
                conn, project_id=_PROJECT, document_key=self.key
            )
            planner = DemandPlanner(self.kernel.model, DataOperationStorage(conn))
            demand = planner.register(
                freeze_demand(
                    self.kernel.model,
                    roots=(selected.root,),
                    targets=("source.pdf/capture",),
                    original_sources=(selected.selection(),),
                    inference=_POLICIES[case],
                    execution_profile=self.kernel.recipe.execution_profile,
                ),
                project=_PROJECT,
                release=self.kernel.prepared.release_id,
                runtime=self.kernel.runtime,
            )
        with self.writer.begin() as conn:
            snapshot = DemandPlanner(self.kernel.model, DataOperationStorage(conn)).resume(
                demand["demand_id"]
            )
        with self.writer.begin() as conn:
            planner = DemandPlanner(self.kernel.model, DataOperationStorage(conn))
            (ready,) = planner.ready(snapshot, authorization=b"{}")
            claim = DataOperationStorage(conn).claim_data_requests(
                cast(
                    WireClaimDataRequestsRequest,
                    {
                        "holder": "stage-owner",
                        "lease_seconds": 300,
                        "items": [
                            {
                                "request_id": WireRequestId(json.loads(ready.native)["request_id"]),
                                "generation": json.loads(ready.native)["generation"],
                            }
                        ],
                    },
                )
            )["items"][0]
            assert claim["state"] == "claimed"
            claim = claim["result"]
            fence = wire_attempt_fence(claim)
            store_pdf_original(
                conn,
                task_id=fence["task_id"],
                attempt=fence["attempt"],
                holder=fence["holder"],
                original=self.original,
                recipe_bytes=self.recipe,
            )
            build = begin_pdf_build(
                conn,
                task_id=fence["task_id"],
                attempt=fence["attempt"],
                holder=fence["holder"],
                source_digest=sha256(self.original).hexdigest(),
                recipe_digest=sha256(self.recipe).hexdigest(),
                schema_digest=sha256(native_schema_bytes()).hexdigest(),
                replay_key="product:native",
            )
        self.requests[build.build_id] = _PdfRequest(
            ready, fence, datetime.fromisoformat(claim["lease_until"].replace("Z", "+00:00"))
        )
        return build

    @contextmanager
    def maintained(self, build):
        """Use the real request fence and renewal owner for long staged fixtures."""
        from corpus_structure.orchestrate.data_operations import NativeRequestClaim
        from corpus_structure.semantic.claim_lifetime import ClaimFenceLost, maintained_claims

        request = self.requests[build.build_id]
        claim = NativeRequestClaim(
            **request.fence,
            release_id=build.release_id,
            deadline=request.deadline,
            runtime_id=self.kernel.runtime,
        )

        def renew(connection, owned):
            result = self.renew(connection, build)
            if result["state"] == "lost":
                raise ClaimFenceLost(owned, result["reason"])

        with maintained_claims(self.writer, (claim,), claim.holder, renew=renew) as owner:
            yield owner

    def renew(self, connection, build):
        return DataOperationStorage(connection).renew_data_request(
            {**self.requests[build.build_id].fence, "lease_seconds": 300}
        )

    def reclaim(self, connection, build, *, holder):
        previous = self.requests[build.build_id]
        claimed = DataOperationStorage(connection).claim_data_requests(
            cast(
                WireClaimDataRequestsRequest,
                {
                    "holder": holder,
                    "lease_seconds": 300,
                    "items": [
                        {
                            "request_id": previous.fence["request_id"],
                            "generation": previous.fence["generation"],
                        }
                    ],
                },
            )
        )["items"][0]
        assert claimed["state"] == "claimed"
        claimed = claimed["result"]
        fence = wire_attempt_fence(claimed)
        assert fence["request_id"] == previous.fence["request_id"]
        assert fence["generation"] == previous.fence["generation"]
        assert fence["task_id"] == build.task_id
        assert fence["attempt"] == build.attempt + 1
        self.requests[build.build_id] = _PdfRequest(
            previous.ready,
            fence,
            datetime.fromisoformat(claimed["lease_until"].replace("Z", "+00:00")),
        )
        return fence

    def register_sources(self, build, *, sections=(), membership="direct"):
        """Freeze source projection without executing it or inventing readiness."""
        with self.writer.begin() as conn:
            original = acquire_original_document_selection(
                conn, project_id=_PROJECT, document_key=self.key
            )
            demand = DemandPlanner(self.kernel.model, DataOperationStorage(conn)).register(
                freeze_demand(
                    self.kernel.model,
                    roots=(original.root,),
                    targets=("source.pdf_views/discovery",),
                    original_sources=(original.selection(),),
                    selections=(
                        OperationSelection(
                            "source.pdf_views/discovery",
                            parameters=canonical_bytes(
                                {"sections": list(sections), "membership": membership}
                            ),
                        ),
                    ),
                    inference=self.requests[build.build_id].ready.resolved.inference,
                    execution_profile=self.kernel.recipe.execution_profile,
                ),
                project=_PROJECT,
                release=self.kernel.prepared.release_id,
                runtime=self.kernel.runtime,
            )
        return demand["demand_id"]

    def selected_sources(self, build, *, sections=(), membership="direct"):
        """Consume the completed capture through its actual declared source projector."""
        demand = self.register_sources(build, sections=sections, membership=membership)
        execute_data_demand(
            self.writer,
            demand,
            source_root=ROOT,
            admission_engine=self.admitter,
            project_id=_PROJECT,
            database_capacity=6,
        )
        kind = self.kernel.prepared.index.definitions["DdoSelectedNativeSource"].iri
        contract = self.kernel.identities[kind, "kind"]
        rows, cursor = [], None
        for _ in range(100):
            with self.writer.connect() as conn:
                page = serve_demand_query(
                    conn,
                    DemandQueryRequest(
                        project_id=_PROJECT,
                        demand_id=demand,
                        view="members",
                        limit=100,
                        max_bytes=8 * 1024 * 1024,
                        cursor=cursor,
                    ),
                )
            rows.extend(row for row in page["items"] if row["kind_contract"] == contract)
            cursor = page["continuation"]
            if cursor is None:
                return rows
        raise AssertionError("bounded source projection did not finish its selected pages")

    def complete(self, build, publication):
        """Publish only the actual sealed staging receipt, without provider claims."""
        request = self.requests[build.build_id]
        operation = self.kernel.model.operation(request.ready.operation)
        output = next(role for role in operation.roles if role.direction == "output")
        assert operation.implementation_root is not None
        with self.writer.begin() as conn:
            receipt = inspect_pdf_execution_receipt(
                conn, publication, attempt=build.attempt, holder=build.holder
            )
            reader = PublishedPdfReader(
                conn,
                ProductReference(
                    publication.task_id, publication.product_key, publication.logical_digest
                ),
                projection_context=self.kernel.prepared,
                read_budget=PublishedReadBudget(100, 8 * 1024 * 1024),
            )
            health = [row for row in reader.iter_companions("health") if "conversion" in row]
            assert len(health) == 1
            value = self.kernel.prepared.validate_python(
                "DdoPdfCapture", pdf_publication_value(self.key, publication, health[0])
            ).model_dump(mode="python", exclude_unset=True)
            binding = json.loads(request.ready.binding)
            completion = cast(
                WireCompletion,
                {
                    "outcome": successful_return_outcome(operation),
                    "inputs": binding["inputs"],
                    "support": binding["support"],
                    "implementation_revision": self.kernel.identities[
                        operation.implementation_root, "implementation-slice"
                    ],
                    "outputs": [
                        {
                            "role": output.name,
                            "position": 0,
                            "multiplicity": 1,
                            "product": {
                                "kind_contract": self.kernel.identities[output.kind, "kind"],
                                "body": semantic_value(value),
                                "members": [],
                            },
                        }
                    ],
                    "execution_evidence": bind_execution_evidence(
                        None,
                        fence=dict(request.fence),
                        runtime_id=self.kernel.runtime,
                        pdf_content=canonical_bytes(asdict(receipt)),
                    ),
                },
            )
            storage = DataOperationStorage(conn)
            retained = storage.retain_data_completion_intent(
                {
                    **request.fence,
                    "runtime_id": RuntimeId(self.kernel.runtime),
                    "completion": completion,
                }
            )
            return storage.publish_data_derivation(
                {**request.fence, "intent_id": retained["intent_id"]}
            )


def _private_build_factory(
    commit_db_engine,
    commit_writer_engine,
    tmp_path,
    request,
    *,
    admission_engine,
    kernel_recipe=None,
    source_kind=None,
):
    recipe = current_pdf_recipe(tmp_path) if kernel_recipe is None else kernel_recipe
    with commit_db_engine.begin() as conn:
        kernel = admit_kernel(conn, recipe)
    captured = read_data_operation_inputs(kernel.preparation.dependencies)
    assert captured is not None and captured[1] is not None
    profile = next(
        asset
        for asset in captured[1].boundary_contracts
        if asset.name == "pdf-capture/profile-assets"
    )
    recipe_bytes = bytes.fromhex(json.loads(profile.content)["recipe"])
    path = tmp_path / "source.pdf"
    source_kind = getattr(request, "param", None) if source_kind is None else source_kind
    if source_kind in {
        "renderable_pdf",
        "characterization_pdf",
        "characterization_finalizable_pdf",
    }:
        from pdf_region_support import asymmetric_pdf

        if source_kind in {
            "characterization_pdf",
            "characterization_finalizable_pdf",
        }:
            from io import BytesIO

            from PIL import Image, ImageDraw

            images = [Image.new("RGB", (612, 792), "white") for _ in range(4)]
            try:
                for page in (2, 3):
                    ImageDraw.Draw(images[page]).text((20, 20), "x=1", fill="black")
                output = BytesIO()
                images[0].save(
                    output, format="PDF", save_all=True, append_images=images[1:], resolution=72
                )
                original = output.getvalue()
            finally:
                for image in images:
                    image.close()
        else:
            original = asymmetric_pdf(612, 792)
        path.write_bytes(original)
    else:
        original = b"%PDF-1.7 private staging fixture"
        path.write_bytes(original)

    with commit_writer_engine.begin() as conn:
        DataOperationStorage(conn).initialize_source_project(
            {
                "project_id": ProjectId(_PROJECT),
                "release_id": ReleaseId(kernel.prepared.release_id),
            }
        )
        register_original_document(
            conn,
            prepared=kernel.prepared,
            project_id=_PROJECT,
            source_uri="file:pdf-stage",
            original_path=str(path),
            original=original,
            mime="application/pdf",
        )
    return _PrivatePdfBuildFactory(
        kernel,
        commit_writer_engine,
        admission_engine,
        original,
        recipe_bytes,
        document_key(_PROJECT, "file:pdf-stage", sha256(original).hexdigest()),
    )


@pytest.fixture
def create_private_build(
    commit_db_engine, commit_writer_engine, commit_admitter_engine, tmp_path, request
):
    return _private_build_factory(
        commit_db_engine,
        commit_writer_engine,
        tmp_path,
        request,
        admission_engine=commit_admitter_engine,
    )


@pytest.fixture
def private_build(
    commit_db_engine, commit_writer_engine, commit_admitter_engine, tmp_path, request
):
    return _private_build_factory(
        commit_db_engine,
        commit_writer_engine,
        tmp_path,
        request,
        admission_engine=commit_admitter_engine,
    )()


def native_batch(build, text_value="first"):
    return pa.RecordBatch.from_pylist(
        [
            dict(
                product_id=build.product_id,
                revision_id=build.revision_id,
                record_id="node-1",
                native_type="TextItem",
                family="node",
                native_address="#/texts/0",
                native_address_stream_id=None,
                scalars_json='{"text":"' + text_value + '"}',
                structure_json="{}",
            )
        ],
        schema=stage_schema("native"),
    )
