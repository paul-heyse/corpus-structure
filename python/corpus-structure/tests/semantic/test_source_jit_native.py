"""Actual scheduler leases and shared reader lifetime with controlled method kernels."""

from collections.abc import Iterable, Sequence

from pydantic import BaseModel
from sqlalchemy import text

from corpus_structure.core.method import (
    Digest,
    MethodContext,
    MethodSettings,
    Resources,
    SourceRunContext,
    UnitRef,
    UnitResult,
    UnitView,
)
from corpus_structure.core.vocab import ObservationOutcome, Stage, TaskUnitType
from corpus_structure.methods.math.methods import (
    ExtractMathConfig,
    MathReadingsBatch,
    NormalizeFormulaConfig,
)
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.orchestrate.source_reader import ScopedSourceReader
from corpus_structure.semantic._operation_ids import RunId
from corpus_structure.semantic.claim_lifetime import ClaimOwner
from corpus_structure.semantic.operations import OperationBinding, register_document

from .operation_scenario_support import prepare_operation_scenario


def test_ready_methods_claim_only_current_batch_and_keep_group_reader(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    # Native task/dependency mechanics and real owned reads are exercised here; the
    # controlled kernels establish scheduler behavior, not mathematical extraction.
    # Both independent controlled kernels use the dependency-free extraction
    # configuration; the six-view cases below exercise actual normalization prerequisites.
    prepared = prepare_operation_scenario(semantic_db_engine, observations=True, evaluation=True)
    with semantic_writer_engine.begin() as conn:
        for number in range(6):
            path = tmp_path / f"input-{number}.pdf"
            original = f"%PDF-1.7\nindependent source {number}".encode()
            path.write_bytes(original)
            register_document(
                conn,
                project_id="p",
                source_uri=path.name,
                original_path=str(path),
                original=original,
                mime="application/pdf",
            )
    batches, readers, preparations = [], [], []

    class ControlledMath[C: BaseModel]:
        version = "jit-control-1"
        tier = "deterministic"
        confidence_source = None
        unit_type = TaskUnitType.DOCUMENT
        resources = Resources(batch_size=4)

        def __init__(self, name: str, family: str, config: type[C]):
            self.name, self.family, self.Config = name, family, config

        def select(self, run: SourceRunContext, cfg: C) -> Iterable[UnitRef]:
            return run.reader.documents(tuple(f"input-{number}.pdf" for number in range(6)))

        def input_digest(self, unit: UnitView, cfg: C) -> Digest:
            return Digest(f"independent:{unit.ref.unit_key}".encode())

        def run(
            self, units: Sequence[UnitView], cfg: C, ctx: MethodContext
        ) -> Sequence[UnitResult]:
            with semantic_writer_engine.connect() as conn:
                running = conn.execute(
                    text(
                        "SELECT m.name,t.id FROM ops.task t JOIN ops.method_config c "
                        "ON c.id=t.method_config_id JOIN ops.method m ON m.id=c.method_id "
                        "WHERE t.run_id=:run AND t.status='running'"
                    ),
                    {"run": ctx.run.run_id},
                ).all()
            assert len(running) == len(units) <= 4
            assert {row.name for row in running} == {self.name}
            batches.append((self.name, len(units)))
            readers.append(ctx.reader)
            assert isinstance(ctx.reader, ScopedSourceReader)
            batch = ctx.reader.math_readings_batch
            assert isinstance(batch, MathReadingsBatch)
            batch.bind(ctx.reader)
            preparations.append(batch)
            for unit in units:
                assert unit.ref.unit_id is not None
                assert ctx.reader.original(unit.ref.unit_id).startswith(b"%PDF-")
            return tuple(
                UnitResult(ref=unit.ref, outcome=ObservationOutcome.EMPTY) for unit in units
            )

    registry = MethodRegistry(
        [
            ControlledMath("extract.math", "extract", ExtractMathConfig),
            ControlledMath("normalize.formula", "normalize", ExtractMathConfig),
        ],
        MethodsFile(
            configs={"extract.math": {"default": {}}, "normalize.formula": {"default": {}}},
            sections={"math": {}},
        ),
    )
    result = run_source_methods(
        semantic_writer_engine,
        project_id="p",
        prepared=prepared,
        binding=OperationBinding(prepared.release_id, "z", 0, b"{}"),
        registry=registry,
        graph=Graph(
            ((Stage.EXTRACT, (Step("extract.math/default"), Step("normalize.formula/default"))),)
        ),
        method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
    )
    assert batches == [
        ("extract.math", 4),
        ("extract.math", 2),
        ("normalize.formula", 4),
        ("normalize.formula", 2),
    ]
    assert all(reader is readers[0] for reader in readers)
    assert all(batch is preparations[0] for batch in preparations)
    assert result.status == "source_ready"
    with semantic_db_engine.connect() as conn:
        assert (
            conn.scalar(
                text("SELECT count(*) FROM ops.task WHERE run_id=:run AND status='empty'"),
                {"run": result.run_id},
            )
            == 12
        )


def _run_source_view_dependency_case(admin, writer, directory, monkeypatch, *, reclaim):
    """Six real published views; only mathematical computation is a controlled kernel."""
    from contextlib import contextmanager
    from threading import Event

    import pytest
    from pdf_acceptance_support import publish_controlled_pdf_views, write_controlled_pdf

    from corpus_structure.core.method import ObservationDraft
    from corpus_structure.semantic import claim_lifetime, operations
    from corpus_structure.semantic.operations import OperationConflict, claim_tasks, complete_task

    class PublicationConfig(BaseModel):
        pass

    class SchedulerReport(BaseModel):
        stage: str

    prepared = prepare_operation_scenario(admin, observations=True, evaluation=True)
    paragraphs = tuple(f"Independently authored section {number}." for number in range(6))
    original = write_controlled_pdf(directory / "source.pdf", paragraphs)
    with writer.begin() as conn:
        document = register_document(
            conn,
            project_id="p",
            source_uri="source.pdf",
            original_path=str(directory / "source.pdf"),
            original=original,
            mime="application/pdf",
        )
    native_views, batches, durable_counts, readiness = [], [], [], []
    readers, preparations, reclaimed = [], [], []
    slow_original, renewal_during_custody = Event(), Event()
    actual_read, actual_renew = operations.read_original, claim_lifetime.renew_claim
    actual_owner = claim_lifetime.maintained_claims
    original_reads = []

    @contextmanager
    def frequent_owner(engine, claims, holder, **values):
        with actual_owner(engine, claims, holder, interval=0.01, **values) as owner:
            yield owner

    def controlled_slow_read(conn, identity, **values):
        original_reads.append(identity)
        if len(original_reads) == 2:
            slow_original.set()
            assert renewal_during_custody.wait(5), "earlier custody locks prevented renewal"
        return actual_read(conn, identity, **values)

    def observed_renewal(conn, **values):
        actual_renew(conn, **values)
        if slow_original.is_set():
            renewal_during_custody.set()

    monkeypatch.setattr(claim_lifetime, "maintained_claims", frequent_owner)
    monkeypatch.setattr(claim_lifetime, "renew_claim", observed_renewal)
    monkeypatch.setattr(operations, "read_original", controlled_slow_read)

    class PublishedSource:
        name, version = "pdf.controlled-source", "jit-views-source-1"
        family, tier = "ingest", "deterministic"
        confidence_source, unit_type, Config = None, TaskUnitType.DOCUMENT, PublicationConfig
        resources = Resources()

        def select(self, run: SourceRunContext, cfg: PublicationConfig) -> Iterable[UnitRef]:
            return run.reader.documents(("source.pdf",))

        def input_digest(self, unit: UnitView, cfg: PublicationConfig) -> Digest:
            return Digest(b"published-six-independent-views")

        def run(
            self, units: Sequence[UnitView], cfg: PublicationConfig, ctx: MethodContext
        ) -> Sequence[UnitResult]:
            owner = ctx.check_active
            assert isinstance(owner, ClaimOwner)
            native_views.extend(
                publish_controlled_pdf_views(
                    writer,
                    prepared=prepared,
                    run_id=ctx.run.run_id,
                    document_id=document,
                    original=original,
                    paragraphs=paragraphs,
                    source_claim=next(iter(owner.active.values())),
                )
            )
            return (UnitResult(ref=units[0].ref, outcome=ObservationOutcome.EMPTY),)

    class ControlledMath[C: BaseModel]:
        version, tier, confidence_source = "jit-views-math-1", "deterministic", None
        unit_type, resources = TaskUnitType.SOURCE_VIEW, Resources(batch_size=4)

        def __init__(self, name: str, family: str, config: type[C]):
            self.name, self.family, self.Config = name, family, config

        def original_recipe(self, config):
            return b'{"recipe":"scheduler-owned-view-original"}'

        def select(self, run: SourceRunContext, cfg: C) -> Iterable[UnitRef]:
            return tuple(
                UnitRef(TaskUnitType.SOURCE_VIEW, ref.id, ref.key)
                for ref in run.reader.source_views()
            )

        def input_digest(self, unit: UnitView, cfg: C) -> Digest:
            return Digest(f"actual-native-view:{unit.ref.unit_key}".encode())

        def run(
            self, units: Sequence[UnitView], cfg: C, ctx: MethodContext
        ) -> Sequence[UnitResult]:
            with writer.connect() as conn:
                rows = (
                    conn.execute(
                        text(
                            "SELECT t.id,t.attempt,t.claimed_by,m.name,t.method_config_id "
                            "FROM ops.task t JOIN ops.method_config c ON c.id=t.method_config_id "
                            "JOIN ops.method m ON m.id=c.method_id "
                            "WHERE t.run_id=:run AND t.status='running' ORDER BY t.id"
                        ),
                        {"run": ctx.run.run_id},
                    )
                    .mappings()
                    .all()
                )
                done = conn.scalar(
                    text(
                        "SELECT count(*) FROM ops.task t "
                        "JOIN ops.method_config c ON c.id=t.method_config_id "
                        "JOIN ops.method m ON m.id=c.method_id WHERE t.run_id=:run "
                        "AND m.name='extract.math' AND t.status='done'"
                    ),
                    {"run": ctx.run.run_id},
                )
                ready = conn.scalar(
                    text(
                        "SELECT count(*) FROM ops.task t "
                        "JOIN ops.method_config c ON c.id=t.method_config_id "
                        "JOIN ops.method m ON m.id=c.method_id WHERE t.run_id=:run "
                        "AND m.name='normalize.formula' AND t.status='pending' "
                        "AND EXISTS(SELECT FROM ops.task_dependency d WHERE d.task_id=t.id) "
                        "AND NOT EXISTS(SELECT FROM ops.task_dependency d JOIN ops.task p "
                        "ON p.id=d.dependency_task_id WHERE d.task_id=t.id "
                        "AND p.status NOT IN ('done','empty','reused'))"
                    ),
                    {"run": ctx.run.run_id},
                )
            assert len(rows) == len(units) <= 4
            assert {row["name"] for row in rows} == {self.name}
            batches.append((self.name, len(units)))
            durable_counts.append(done)
            readiness.append(ready)
            readers.append(ctx.reader)
            assert isinstance(ctx.reader, ScopedSourceReader)
            batch = ctx.reader.math_readings_batch
            assert isinstance(batch, MathReadingsBatch)
            batch.bind(ctx.reader)
            preparations.append(batch)
            if reclaim and self.name == "extract.math" and done == 4:
                assert ready == 4
                victim = rows[0]
                # Administrative clock control changes only lease age. Reclaim and both
                # stale/new fences use the actual protected native operations.
                owner = ctx.check_active
                assert isinstance(owner, ClaimOwner)
                with owner.lock:
                    with admin.begin() as conn:
                        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
                        conn.execute(
                            text(
                                "UPDATE ops.task "
                                "SET lease_until=clock_timestamp()-interval '1 second' "
                                "WHERE id=:id"
                            ),
                            {"id": victim["id"]},
                        )
                    with writer.begin() as conn:
                        (replacement,) = claim_tasks(
                            conn,
                            run_id=RunId(ctx.run.run_id),
                            config_id=victim["method_config_id"],
                            holder="source-view-reclaimer",
                            limit=1,
                            prepared=prepared,
                        )
                    assert replacement.task_id == victim["id"]
                    assert replacement.attempt == victim["attempt"] + 1
                    with pytest.raises(OperationConflict), writer.begin() as conn:
                        complete_task(
                            conn,
                            task_id=victim["id"],
                            attempt=victim["attempt"],
                            holder=victim["claimed_by"],
                            prepared=prepared,
                            observations=(),
                            outcome="empty",
                        )
                    reclaimed.append((victim, replacement))
            return tuple(
                UnitResult(
                    ref=unit.ref,
                    outcome=ObservationOutcome.PRODUCED,
                    observations=(
                        ObservationDraft(
                            kind="record" if self.name == "extract.math" else "value",
                            payload=SchedulerReport(stage=self.name),
                            payload_class=SchedulerReport,
                            payload_version="1",
                            source_view_id=unit.ref.unit_id,
                        ),
                    ),
                )
                for unit in units
            )

    registry = MethodRegistry(
        [
            PublishedSource(),
            ControlledMath("extract.math", "extract", ExtractMathConfig),
            ControlledMath("normalize.formula", "normalize", NormalizeFormulaConfig),
        ],
        MethodsFile(
            configs={
                "pdf.controlled-source": {"default": {}},
                "extract.math": {"default": {}},
                "normalize.formula": {"default": {}},
            },
            sections={"math": {}},
        ),
    )
    values = dict(
        project_id="p",
        prepared=prepared,
        binding=OperationBinding(prepared.release_id, "z", 0, b"{}"),
        registry=registry,
        graph=Graph(
            (
                (Stage.INGEST, (Step("pdf.controlled-source/default"),)),
                (Stage.EXTRACT, (Step("extract.math/default"), Step("normalize.formula/default"))),
            )
        ),
        method_settings=MethodSettings(data_dir=directory, model_cache=directory),
    )
    result = None
    if reclaim:
        with pytest.raises(OperationConflict):
            run_source_methods(writer, **values)
    else:
        result = run_source_methods(writer, **values)
        assert result.status == "source_ready"
    assert len(native_views) == 6 and len({view.ref.id for view in native_views}) == 6
    assert renewal_during_custody.is_set()
    assert batches[:2] == [("extract.math", 4), ("extract.math", 2)]
    assert durable_counts[:2] == [0, 4] and readiness[1] == 4
    assert all(reader is readers[0] for reader in readers)
    assert all(batch is preparations[0] for batch in preparations)
    with admin.connect() as conn:
        if reclaim:
            ((victim, replacement),) = reclaimed
            assert (
                conn.scalar(
                    text(
                        "SELECT count(*) FROM kb.observation o JOIN ops.task t ON t.id=o.task_id "
                        "JOIN ops.method_config c ON c.id=t.method_config_id "
                        "JOIN ops.method m ON m.id=c.method_id "
                        "WHERE t.run_id=:run AND m.name='extract.math' AND t.status='done'"
                    ),
                    {"run": replacement.run_id},
                )
                == 4
            )
            assert (
                conn.scalar(text("SELECT attempt FROM ops.task WHERE id=:id"), {"id": victim["id"]})
                == replacement.attempt
            )
        else:
            assert result is not None
            assert batches == [
                ("extract.math", 4),
                ("extract.math", 2),
                ("normalize.formula", 4),
                ("normalize.formula", 2),
            ]
            assert (
                conn.scalar(
                    text(
                        "SELECT count(*) FROM ops.task_dependency d "
                        "JOIN ops.task t ON t.id=d.task_id "
                        "WHERE t.run_id=:run AND d.kind='source_view_interpretation'"
                    ),
                    {"run": result.run_id},
                )
                == 6
            )
            assert (
                conn.scalar(
                    text(
                        "SELECT count(*) FROM kb.observation o JOIN ops.task t ON t.id=o.task_id "
                        "WHERE t.run_id=:run"
                    ),
                    {"run": result.run_id},
                )
                == 12
            )


def test_six_published_views_keep_current_claims_and_native_dependencies(
    semantic_db_engine, semantic_writer_engine, tmp_path, monkeypatch
):
    _run_source_view_dependency_case(
        semantic_db_engine, semantic_writer_engine, tmp_path, monkeypatch, reclaim=False
    )


def test_source_view_reclaim_preserves_prior_batch_and_refuses_stale_completion(
    semantic_db_engine, semantic_writer_engine, tmp_path, monkeypatch
):
    _run_source_view_dependency_case(
        semantic_db_engine, semantic_writer_engine, tmp_path, monkeypatch, reclaim=True
    )
