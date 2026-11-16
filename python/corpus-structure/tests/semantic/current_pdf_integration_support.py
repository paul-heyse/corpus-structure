"""Current claimed PDF requests with a finite controlled provider boundary.

Capture, organization, recognition retention, integration and publication use their
production paths. The scripted document/answers establish transport and custody,
not Docling/Nemotron accuracy or verified external provider execution.
"""

import json
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from hashlib import sha256
from pathlib import Path
from typing import Any

from conftest import settings_for_native_clone
from sqlalchemy import text

from corpus_structure.core.method import MethodSettings
from corpus_structure.ingest.pdf import PdfRecipe
from corpus_structure.ingest.pdf_assets import PreparedPdfAssets
from corpus_structure.ingest.pdf_hierarchy import SectionPolicy
from corpus_structure.ingest.pdf_recognition import NemotronRecipe, RecognitionPage
from corpus_structure.ingest.pdf_stream_types import PdfStreamReply
from corpus_structure.ingest.pdf_streaming import PdfStreamSpool, StreamingPdfResult
from corpus_structure.orchestrate.source_operation import run_source_operation
from corpus_structure.orchestrate.source_request import SourceRunRequest, WholeDocument
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_artifacts import capture_port_generator_sources
from corpus_structure.semantic.data_operation_identity import decode_semantic_value
from corpus_structure.semantic.data_operation_service import read_data_demand
from corpus_structure.semantic.data_operation_storage import (
    native_operation_declarations,
    native_protocol_sources,
)
from corpus_structure.semantic.pdf_capture import pdf_capture_inputs, pdf_capture_operation_sources
from corpus_structure.semantic.pdf_domain import pdf_domain_dependencies
from corpus_structure.semantic.pdf_transforms import (
    PdfEnrichmentOptions,
    PdfIntegrationOptions,
    PdfRecognitionOptions,
    PdfRecognitionResources,
    pdf_transform_operation_sources,
)
from corpus_structure.semantic.pdf_views import pdf_views_operation_sources
from corpus_structure.semantic.primary_operations import combine_primary_sources
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_discovery import source_discovery_inputs
from corpus_structure.semantic.types import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)
from semantic.data_operation_kernel_support import CapturedKernelInputs, Kernel, KernelRecipe
from semantic.data_operation_original_support import OriginalSeedRecipe
from semantic.pdf_native_source_support import IMAGE, make_native_source

ROOT = Path(__file__).resolve().parents[4]


def current_pdf_recipe(directory, *, integration_policy=None):
    native = PdfRecipe(
        "0" * 40,
        "1" * 40,
        device="cpu",
        ocr_device="cpu",
        recipe_id="docling-standard-pdf-stream-v1",
    )
    assets = PreparedPdfAssets(directory, b"{}", ())
    capture = pdf_capture_operation_sources(native, assets, directory=directory / "owned")
    organization = pdf_transform_operation_sources(
        "organized",
        options=SectionPolicy("explicit-native-headings"),
        directory=directory / "owned",
    )
    enriched = pdf_transform_operation_sources(
        "enriched",
        recipe=native,
        assets=assets,
        options=PdfEnrichmentOptions(),
        directory=directory / "owned",
        input_operation="source.pdf_sections/organize",
    )
    worker = directory / "explicit-provider.py"
    worker.write_text(
        "raise AssertionError('controlled provider boundary must replace inference')\n"
    )
    integration = pdf_transform_operation_sources(
        "integrated",
        recognition_recipe=NemotronRecipe("2" * 64, "3" * 64),
        options=PdfIntegrationOptions(
            integration_policy={} if integration_policy is None else integration_policy
        ),
        recognition_options=PdfRecognitionOptions(recovery_policy=None),
        resources=PdfRecognitionResources(
            python=sys.executable,
            script=str(worker),
            endpoint="http://127.0.0.1:8123/v1",
            receipts=str(directory / "receipts"),
            timeout_seconds=1,
        ),
        directory=directory / "owned",
        input_operation="source.pdf_sections/organize",
    )
    sources = combine_primary_sources(
        pdf_views_operation_sources(capture, mode="organized", transformation_sources=organization),
        pdf_views_operation_sources(capture, mode="enriched", transformation_sources=enriched),
        pdf_views_operation_sources(capture, mode="integrated", transformation_sources=integration),
    )
    bundle = source_discovery_inputs(
        pdf_capture_inputs(
            SourceBundle(
                "toy_semantic",
                (
                    SourceArtifact(
                        "toy_semantic", (ROOT / "domains/toy/semantic.yaml").read_bytes()
                    ),
                    SourceArtifact(
                        "semantic_core",
                        (
                            ROOT
                            / "python/corpus-structure/src/corpus_structure/model/semantic/core.yaml"
                        ).read_bytes(),
                    ),
                ),
            )
        )
    )
    native_sources = native_protocol_sources()
    dependencies = pdf_domain_dependencies(ResolvedDependencies())
    dependencies = data_operation_dependencies(
        ResolvedDependencies(
            (*dependencies.artifacts, *native_sources, *capture_port_generator_sources())
        ),
        (native_operation_declarations(native_sources),),
        sources,
    )
    return KernelRecipe(
        "controlled-pdf-transform-demand",
        "",
        None,
        "",
        project_id=None,
        execution_profile="source-native",
        captured_inputs=CapturedKernelInputs(
            bundle, dependencies, PreparationProfile(version="semantic-2")
        ),
    )


RICH_RESPONSE = (
    b"<x_0.05><y_0.03>equal<x_0.30><y_0.07><class_Text>"
    b"<x_0.05><y_0.13>equal<x_0.30><y_0.17><class_Text>"
    b"<x_0.05><y_0.333333>\\begin{tabular}{cc}$x+1$ & 2\\end{tabular}"
    b"<x_0.55><y_0.4><class_Table>"
    b'<x_0.6><y_0.55><chart type="line">\n| Time | Speed (m/s) |\n|---|---|\n|1|2|'
    b"<x_0.95><y_0.9><class_Chart>"
    b"<x_0.6><y_0.2>Value $y+2$ follows<x_0.95><y_0.25><class_Text>"
)


@dataclass
class CurrentPdfIntegration:
    kernel: Any
    clone: Any
    original: Any
    settings: Any
    directory: Path
    calls: list[str] = field(default_factory=list)
    observations: list[tuple[ProductReference, Any]] = field(default_factory=list)
    claims: dict[str, Any] = field(default_factory=dict)
    drafts: dict[str, Any] = field(default_factory=dict)
    publications: dict[str, ProductReference] = field(default_factory=dict)
    values: dict[str, dict] = field(default_factory=dict)
    demand_id: str | None = None
    failure: Any = None
    snapshot: Any = None
    observation_source: Any = None
    reclaimed_fence: Any = None
    interruption: Any = None

    @property
    def prepared(self):
        return self.kernel.prepared

    def reader(self):
        return self.kernel.purpose("read")


def remap_current_integration(case, policy):
    """Admit and execute a real policy-only consumer of this actual source."""
    from semantic.current_pdf_source_support import admit_current_target

    kernel = admit_current_target(
        case,
        current_pdf_recipe(case.directory, integration_policy=policy),
        case.directory / "policy-consumer",
    )
    request = SourceRunRequest(
        project_id=case.original.project_id,
        release_id=kernel.prepared.release_id,
        runtime_id=kernel.runtime,
        domain="toy",
        workflow="capture",
        selection=WholeDocument(),
        documents=(case.original.document_key,),
        pdf_mode="integrated",
        recognition_pages=(1,),
        targets=("source.pdf_integrated_views/discovery",),
    )
    with open_runtime_engine(
        case.settings, "current-policy-remap", purpose="write", max_size=6
    ) as engine:
        result = run_source_operation(
            engine,
            request,
            MethodSettings(data_dir=case.directory, model_cache=case.directory),
            source_root=ROOT,
            admission_engine=kernel.purpose("admit"),
        )
    with case.reader().begin() as connection:
        snapshot = read_data_demand(connection, result.demand_id, view="products")
    return kernel, snapshot


@contextmanager
def current_integration_journey(
    scenario_seeds,
    tmp_path,
    monkeypatch,
    native_settings,
    *,
    raw_responses=(RICH_RESPONSE, RICH_RESPONSE),
    outcome="succeeded",
    before_draft=None,
    before_observation=None,
    expect_unresolved_page=False,
    reclaim_after_recognition=False,
    candidate_pages=(),
):
    from corpus_structure.ingest import pdf_recognition, pdf_worker
    from corpus_structure.orchestrate import pdf_streaming
    from corpus_structure.semantic import pdf_integrated

    target = OriginalSeedRecipe(current_pdf_recipe(tmp_path))
    with scenario_seeds.commit_clone(target) as clone, monkeypatch.context() as patches:
        kernel = Kernel(
            clone.admin,
            clone.stage.kernel.preparation,
            clone.stage.kernel.identities,
            target.target,
            clone,
        )
        original = clone.stage.original.reference
        settings = settings_for_native_clone(native_settings, clone.admin.url.database)
        case = CurrentPdfIntegration(kernel, clone, original, settings, tmp_path)

        def controlled_stream(
            self,
            source,
            *,
            spool_root,
            record_root,
            build_id,
            release_id,
            on_replay,
            check_active,
            **options,
        ):
            from docling_core.types.doc import DoclingDocument

            check_active()
            case.calls.append("capture")
            supplied = make_native_source(source.path.read_bytes())
            document = DoclingDocument.model_validate(supplied.payload["document"])
            document.pages.pop(2)
            document.texts[0].prov = document.texts[0].prov[:1]
            document.add_heading(text="1 Controlled", level=1)
            # The independent fixture retains equal text in distinct native cells.
            assert document.tables[0].data.table_cells[0].text == "equal"
            spool = PdfStreamSpool(spool_root, on_page=on_replay, check_active=check_active)
            for page in candidate_pages:
                spool.capture_candidates(page)
            streamed = StreamingPdfResult(
                document,
                spool,
                "success",
                (),
                self.recipe.to_bytes(),
                (),
            )
            occurrences = streamed.write_native_occurrence_batches(
                record_root.with_name(record_root.name + "-occurrences"),
                build_id=build_id,
                on_batch=on_replay,
            )
            records = streamed.write_record_batches(
                record_root,
                build_id=build_id,
                release_id=release_id,
                source_digest=source.digest,
                on_batch=on_replay,
            )
            return PdfStreamReply("success", (), self.recipe.to_bytes(), (), records + occurrences)

        def controlled_recognition(self, source, recipe, pages, *, check_active, **options):
            assert tuple(pages) == (1,)
            # This controlled external boundary retains actual request/report
            # bytes. Reuse is explicit and confined to the exact source+recipe.
            directory = (
                tmp_path
                / "controlled-actual-requests"
                / source.digest
                / recipe.digest
                / "page-00001"
            )
            reused = directory.is_dir()
            if reused:
                case.calls.append("recognition-adopt")
                result = json.loads((directory / "result.json").read_bytes())
            else:
                case.calls.append("recognize")
                directory.mkdir(parents=True)
                (directory / "submitted.png").write_bytes(IMAGE)
                requests = []
                for ordinal, raw in enumerate(raw_responses):
                    row = dict(
                        ordinal=ordinal,
                        stage="fullpage" if ordinal == 0 else "detection",
                        outcome="succeeded" if raw is not None else "failed",
                        submitted_image="submitted.png",
                        submitted_digest=sha256(IMAGE).hexdigest(),
                        width=4,
                        height=6,
                        prompt="Independent finite controlled recognition",
                        settings={},
                    )
                    if raw is not None:
                        name = f"response-{ordinal:03d}.txt"
                        (directory / name).write_bytes(raw)
                        row.update(
                            raw_response=name,
                            raw_digest=sha256(raw).hexdigest(),
                            finish_reason="stop",
                        )
                    else:
                        row["diagnostic"] = "controlled connection closed before response"
                    (directory / f"request-{ordinal:03d}.json").write_text(json.dumps(row))
                    requests.append(row)
                result = {"outcome": outcome, "requests": requests}
                (directory / "result.json").write_text(json.dumps(result))
            check_active()
            yield RecognitionPage(
                1,
                directory,
                result,
                dict(
                    status="coarse",
                    normalization="none",
                    source_space="pdf_points",
                    target_space="submitted_pixels",
                    page_width=200.0,
                    page_height=300.0,
                    page_rotation=0,
                    crop_left=0.0,
                    crop_top=0.0,
                    crop_right=200.0,
                    crop_bottom=300.0,
                    affine=[0.02, 0.0, 0.0, 0.02, 0.0, 0.0],
                ),
                reused=reused,
            )

        publish_observation = pdf_integrated.store_pdf_observation

        def retain_observation(connection, **arguments):
            if before_observation is not None:
                before_observation(case, connection, arguments)
            digest = publish_observation(connection, **arguments)
            product = arguments["product"]
            case.observations.append(
                (
                    ProductReference(arguments["task_id"], product.values()["product_key"], digest),
                    product,
                )
            )
            return digest

        publish_draft = pdf_streaming.publish_pdf_record_draft

        def retained_draft(engine, claim, holder, draft, **arguments):
            # A small finite fixture materializes its actual Arrow journal once.
            # Publication still consumes the same rows through the real writer.
            draft = replace(
                draft,
                companions={
                    family: tuple(rows) for family, rows in (draft.companions or {}).items()
                },
                metadata={
                    **(draft.metadata or {}),
                    **(
                        {"inline_candidate_pages": tuple(draft.metadata["inline_candidate_pages"])}
                        if draft.metadata and "inline_candidate_pages" in draft.metadata
                        else {}
                    ),
                },
            )
            case.claims[draft.product_key] = claim
            case.drafts[draft.product_key] = draft
            if before_draft is not None:
                before_draft(case, engine, claim, holder, draft, arguments, publish_draft)
            publication = publish_draft(engine, claim, holder, draft, **arguments)
            case.publications[draft.product_key] = ProductReference(
                publication.task_id, publication.product_key, publication.logical_digest
            )
            return publication

        patches.setattr(pdf_worker.PdfWorker, "stream", controlled_stream)
        patches.setattr(
            pdf_recognition.RecognitionWorker, "_recognize_pages", controlled_recognition
        )
        patches.setattr(pdf_integrated, "store_pdf_observation", retain_observation)
        patches.setattr(pdf_streaming, "publish_pdf_record_draft", retained_draft)
        if reclaim_after_recognition:
            from typing import cast

            from corpus_structure.orchestrate.data_operations import NativeDemandExecutor
            from corpus_structure.semantic._data_operation_wire import WireClaimDataRequestRequest
            from corpus_structure.semantic.data_operation_storage import DataOperationStorage

            retain_answer = NativeDemandExecutor._retain_answer

            def reclaim(executor, ready, claim, answer, port, owner, *, physical):
                if (
                    ready.operation == "source.pdf_recognition/observe"
                    and case.reclaimed_fence is None
                ):
                    # The provider/CPU work has returned and all raw publications
                    # committed. Expiry+new claim share the existing support-lock
                    # order, so the old heartbeat cannot race this fixture step.
                    with case.clone.admin.begin() as connection:
                        connection.execute(
                            text("SELECT ops.require_pdf_stage_owner(:task,:attempt,:holder)"),
                            {
                                "task": claim.task_id,
                                "attempt": claim.attempt,
                                "holder": claim.holder,
                            },
                        )
                        connection.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
                        assert (
                            connection.execute(
                                text(
                                    "UPDATE ops.task SET lease_until=clock_timestamp()-interval '1 second' WHERE id=:task"
                                ),
                                {"task": claim.task_id},
                            ).rowcount
                            == 1
                        )
                        connection.exec_driver_sql("SET LOCAL ROLE corpus_sem_writer")
                        changed = DataOperationStorage(connection).claim_data_request(
                            cast(
                                WireClaimDataRequestRequest,
                                dict(
                                    request_id=claim.request_id,
                                    generation=claim.generation,
                                    holder="recognition-successor",
                                    lease_seconds=300,
                                ),
                            )
                        )
                        assert changed["state"] == "claimed"
                        case.reclaimed_fence = {
                            name: changed[name]
                            for name in ("request_id", "generation", "task_id", "attempt", "holder")
                        }
                    import pytest
                    from psycopg import Error as NativePgError
                    from sqlalchemy.exc import DBAPIError

                    # An actual native call from the old holder refuses before
                    # replay can return any previously retained observation.
                    with case.kernel.purpose("write").begin() as connection:
                        with pytest.raises(DBAPIError) as stale, connection.begin_nested():
                            publish_observation(
                                connection,
                                task_id=claim.task_id,
                                attempt=claim.attempt,
                                holder=claim.holder,
                                runtime_id=executor.runtime.runtime_id,
                                product=case.observations[0][1],
                            )
                        assert isinstance(stale.value.orig, NativePgError)
                        assert stale.value.orig.sqlstate == "P0004"
                return retain_answer(executor, ready, claim, answer, port, owner, physical=physical)

            patches.setattr(NativeDemandExecutor, "_retain_answer", reclaim)
        request = SourceRunRequest(
            project_id=original.project_id,
            release_id=kernel.prepared.release_id,
            runtime_id=kernel.runtime,
            domain="toy",
            workflow="capture",
            selection=WholeDocument(),
            documents=(original.document_key,),
            pdf_mode="integrated",
            recognition_pages=(1,),
            targets=("source.pdf_integrated_views/discovery",),
        )
        with open_runtime_engine(
            settings, "current-rich-pdf-integration", purpose="write", max_size=6
        ) as engine:
            from corpus_structure.orchestrate.data_operations import NativeDemandExecutionError

            try:
                result = run_source_operation(
                    engine,
                    request,
                    MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
                    source_root=ROOT,
                    admission_engine=kernel.purpose("admit"),
                )
            except NativeDemandExecutionError as error:
                if reclaim_after_recognition and case.reclaimed_fence is not None:
                    from corpus_structure.semantic.claim_lifetime import ClaimFenceLost

                    assert any(isinstance(failure, ClaimFenceLost) for failure in error.failures)
                    case.interruption = error
                    with case.clone.admin.begin() as connection:
                        connection.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
                        assert (
                            connection.execute(
                                text(
                                    "UPDATE ops.task SET lease_until=clock_timestamp()-interval '1 second' WHERE id=:task"
                                ),
                                {"task": case.reclaimed_fence["task_id"]},
                            ).rowcount
                            == 1
                        )
                    from corpus_structure.semantic.data_operation_service import execute_data_demand

                    result = execute_data_demand(
                        engine,
                        error.result.demand_id,
                        source_root=ROOT,
                        admission_engine=kernel.purpose("admit"),
                        database_capacity=6,
                    )
                elif not expect_unresolved_page:
                    raise
                else:
                    assert any(
                        isinstance(failure, RuntimeError)
                        and str(failure) == "unresolved triple-pass physical pages: [1]"
                        for failure in error.failures
                    )
                    case.failure = error
                    result = error.result
            else:
                assert not expect_unresolved_page, "failed page unexpectedly completed integration"
        case.demand_id = result.demand_id
        with case.reader().begin() as connection:
            assert connection.scalar(text("SELECT current_user")) == "corpus_sem_reader"
            snapshot = read_data_demand(connection, result.demand_id, view="products")
            from corpus_structure.serve.selected_pdf import (
                SelectedPdfSourceReference,
                acquire_selected_pdf_observations,
                acquire_selected_pdf_source,
            )

            obligations = {row["obligation_id"]: row for row in snapshot["obligations"]}
            raw_use = next(
                use
                for use in snapshot["uses"]
                if use["fate"] == "fulfilled"
                and obligations[use["obligation_id"]]["operation_id"] == "source.pdf/capture"
            )
            raw_output = next(
                product for product in raw_use["products"] if product["role"] == "result"
            )
            assert raw_use["derivation_id"] is not None
            acquired = acquire_selected_pdf_source(
                connection,
                SelectedPdfSourceReference(
                    project_id=original.project_id,
                    demand_id=result.demand_id,
                    read_id=snapshot["read_id"],
                    use_id=raw_use["use_id"],
                    product_id=raw_output["product_id"],
                    derivation_id=raw_use["derivation_id"],
                ),
            )
            case.publications["native"] = acquired.physical
            observed_use = next(
                use
                for use in snapshot["uses"]
                if use["fate"] == "fulfilled"
                and obligations[use["obligation_id"]]["operation_id"]
                == "source.pdf_recognition/observe"
            )
            observed_output = next(
                product for product in observed_use["products"] if product["role"] == "result"
            )
            assert observed_use["derivation_id"] is not None
            case.observation_source = acquire_selected_pdf_observations(
                connection,
                SelectedPdfSourceReference(
                    project_id=original.project_id,
                    demand_id=result.demand_id,
                    read_id=snapshot["read_id"],
                    use_id=observed_use["use_id"],
                    product_id=observed_output["product_id"],
                    derivation_id=observed_use["derivation_id"],
                ),
            )
        case.snapshot = snapshot
        obligations = {row["obligation_id"]: row for row in snapshot["obligations"]}
        for use in snapshot["uses"]:
            if use["fate"] != "fulfilled":
                continue
            operation = obligations[use["obligation_id"]]["operation_id"]
            case.values[operation] = {
                product["role"]: decode_semantic_value(product["body"])
                for product in use["products"]
            }
        yield case
