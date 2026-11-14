"""Actual native claim frontiers and private reader lifetimes with controlled kernels."""

from collections import Counter
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
from semantic.operation_scenario_support import prepare_operation_scenario


def _current_claim_rows(writer, ctx, units, method, policy):
    """Query actual owned claim identities separately from the global running window."""
    owner = ctx.check_active
    assert isinstance(owner, ClaimOwner)
    owner()
    with owner.lock:
        claims = tuple(owner.active.values())
    assert len(claims) == len(units) == 1
    with writer.connect() as conn:
        rows = (
            conn.execute(
                text(
                    "SELECT t.id,t.unit_id,t.unit_type,t.attempt,t.claimed_by,m.name,"
                    "t.method_config_id,c.config_hash FROM ops.task t "
                    "JOIN ops.method_config c ON c.id=t.method_config_id "
                    "JOIN ops.method m ON m.id=c.method_id "
                    "WHERE t.run_id=:run AND t.status='running' "
                    "AND t.id=ANY(CAST(:owned AS bigint[])) ORDER BY t.id"
                ),
                dict(run=ctx.run.run_id, owned=[claim.task_id for claim in claims]),
            )
            .mappings()
            .all()
        )
        running = conn.scalar(
            text("SELECT count(*) FROM ops.task WHERE run_id=:run AND status='running'"),
            dict(run=ctx.run.run_id),
        )
    assert len(rows) == len(claims)
    assert {(row["id"], row["attempt"], row["claimed_by"]) for row in rows} == {
        (claim.task_id, claim.attempt, claim.holder) for claim in claims
    }
    assert {(row["unit_type"], row["unit_id"]) for row in rows} == {
        (unit.ref.unit_type.value, unit.ref.unit_id) for unit in units
    }
    assert {row["name"] for row in rows} == {method}
    assert len(claims) <= running <= policy.max_claims
    return owner, claims, rows, running


def _controlled_math_batch(reader, identity):
    # This is an actual controlled consumer of the production reader property and
    # strict binding contract, rather than a stand-alone cache lookalike. The old
    # orchestrator injection fails bind() when a second live claim reader arrives.
    batch = reader.math_readings_batch
    if batch is None:
        batch = MathReadingsBatch()
        reader.math_readings_batch = batch
    batch.bind(reader)
    assert batch.owner is reader
    assert not batch.native, "another claim leaked mutable mathematical state"
    marker = object()
    batch.native[identity] = (marker,)
    assert reader.math_readings_batch.native[identity] == (marker,)
    return batch


def test_ready_methods_claim_only_current_batch_and_keep_group_reader(
    commit_db_engine, commit_writer_engine, tmp_path
):
    # Native task/dependency mechanics and real owned reads are exercised here; the
    # controlled kernels establish scheduler behavior, not mathematical extraction.
    # Both independent controlled kernels use the dependency-free extraction
    # configuration; the six-view cases below exercise actual normalization prerequisites.
    prepared = prepare_operation_scenario(commit_db_engine, observations=True, evaluation=True)
    with commit_writer_engine.begin() as conn:
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
    from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy

    policy = CharacterizationExecutionPolicy()
    assert policy.max_claims == 8
    batches, readers, running_windows, caches = [], [], [], []
    invoked_units = []

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
            _owner, claims, _rows, running = _current_claim_rows(
                commit_writer_engine, ctx, units, self.name, policy
            )
            running_windows.append(running)
            batches.append((self.name, len(units)))
            readers.append(ctx.reader)
            assert isinstance(ctx.reader, ScopedSourceReader)
            assert ctx.reader.prepared is prepared
            caches.append(_controlled_math_batch(ctx.reader, (self.name, units[0].ref.unit_id)))
            invoked_units.extend((self.name, claim.unit_id) for claim in claims)
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
        commit_writer_engine,
        project_id="p",
        prepared=prepared,
        binding=OperationBinding(prepared.release_id, "z", 0, b"{}"),
        registry=registry,
        graph=Graph(
            ((Stage.EXTRACT, (Step("extract.math/default"), Step("normalize.formula/default"))),)
        ),
        method_settings=MethodSettings(
            data_dir=tmp_path, model_cache=tmp_path, execution_policy=policy
        ),
    )
    assert Counter(batches) == {("extract.math", 1): 6, ("normalize.formula", 1): 6}
    assert len(invoked_units) == len(set(invoked_units)) == 12
    assert {identity for name, identity in invoked_units if name == "extract.math"} == {
        identity for name, identity in invoked_units if name == "normalize.formula"
    }
    assert max(running_windows) > 1
    assert len({id(reader) for reader in readers}) == len(readers)
    assert len({id(cache) for cache in caches}) == len(readers)
    assert all(len(cache.native) == 1 for cache in caches)
    caches[0].native.clear()
    assert all(len(cache.native) == 1 for cache in caches[1:])
    assert result.status == "source_ready"
    with commit_db_engine.connect() as conn:
        assert (
            conn.scalar(
                text("SELECT count(*) FROM ops.task WHERE run_id=:run AND status='empty'"),
                {"run": result.run_id},
            )
            == 12
        )


def _run_source_view_dependency_case(admin, writer, directory, monkeypatch, *, reclaim):
    """Six real published views; only mathematical computation is a controlled kernel."""
    from concurrent.futures import Future
    from contextlib import contextmanager
    from threading import Event
    from time import monotonic

    import pytest
    from pdf_acceptance_support import publish_controlled_pdf_views, write_controlled_pdf

    from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
    from corpus_structure.core.method import ObservationDraft
    from corpus_structure.core.work import PreparedWork
    from corpus_structure.semantic import claim_lifetime, operations
    from corpus_structure.semantic.operations import (
        BoundReader,
        OperationConflict,
        claim_tasks,
        complete_task,
        complete_unit_result,
        create_task,
    )

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
    policy = CharacterizationExecutionPolicy()
    assert policy.max_claims == 8
    native_views, batches, running_windows, readers, reclaimed, caches = [], [], [], [], [], []
    original_claims, ready_snapshots, decoys = {}, [], []
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

    class GateReply:
        def __init__(self):
            self.future: Future[None] = Future()
            self.future.set_result(None)

        def collect(self):
            return self.future.result()

        def cancel(self):
            self.future.cancel()

        def retire(self):
            return self.future.done()

    def first_four_dependencies(run_id):
        first = [view.ref.id for view in native_views[:4]]
        with writer.connect() as conn:
            parents = (
                conn.execute(
                    text(
                        "SELECT t.id,t.unit_id,t.status FROM ops.task t "
                        "JOIN ops.method_config c ON c.id=t.method_config_id "
                        "JOIN ops.method m ON m.id=c.method_id WHERE t.run_id=:run "
                        "AND m.name='extract.math' AND t.input_hash<>'decoy' "
                        "AND t.unit_id=ANY(CAST(:first AS bigint[]))"
                    ),
                    dict(run=run_id, first=first),
                )
                .mappings()
                .all()
            )
            children = (
                conn.execute(
                    text(
                        "SELECT child.id,child.unit_id,parent.id AS parent_id,"
                        "parent.unit_id AS parent_unit "
                        "FROM ops.task child JOIN ops.method_config c "
                        "ON c.id=child.method_config_id "
                        "JOIN ops.method m ON m.id=c.method_id "
                        "JOIN ops.task_dependency d ON d.task_id=child.id "
                        "JOIN ops.task parent ON parent.id=d.dependency_task_id "
                        "WHERE child.run_id=:run AND m.name='normalize.formula' "
                        "AND d.kind='source_view_interpretation' AND parent.status='done' "
                        "AND parent.input_hash<>'decoy' "
                        "AND parent.unit_id=ANY(CAST(:first AS bigint[]))"
                    ),
                    dict(run=run_id, first=first),
                )
                .mappings()
                .all()
            )
        assert len(parents) == 4
        if not all(parent["status"] == "done" for parent in parents) or len(children) < 4:
            return None
        expected = {(parent["unit_id"], parent["id"]) for parent in parents}
        assert len(children) == 4
        assert {(child["unit_id"], child["parent_id"]) for child in children} == expected
        assert all(child["unit_id"] == child["parent_unit"] for child in children)
        return expected

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
            if self.name == "normalize.formula":
                assert unit.ref.unit_id is not None
                reader = unit.run.reader
                assert isinstance(reader, BoundReader)
                upstream = reader.source_result(unit.ref.unit_id, "extract.math")
                assert upstream is not None and upstream["input_hash"] != "decoy"
            return Digest(f"actual-native-view:{unit.ref.unit_key}".encode())

        def plan(self, units, cfg, ctx):
            assert len(native_views) == 6 and len(units) == 1
            # Keep default eight-claim concurrency. Only the final two producer
            # kernels wait, cooperatively, for actual prior native settlement and
            # child registration; no worker/thread or global scheduling gate exists.
            if self.name == "extract.math" and units[0].ref.unit_id in {
                view.ref.id for view in native_views[4:]
            }:
                deadline = monotonic() + 10

                def try_gate():
                    ctx.check_active()
                    assert monotonic() < deadline, "prior native source dependencies did not settle"
                    ready = first_four_dependencies(ctx.run.run_id)
                    if ready is None:
                        return None
                    ready_snapshots.append(ready)
                    return GateReply()

                yield (PreparedWork(try_gate),)
            return self.run(units, cfg, ctx)

        def run(
            self, units: Sequence[UnitView], cfg: C, ctx: MethodContext
        ) -> Sequence[UnitResult]:
            owner, claims, rows, running = _current_claim_rows(
                writer, ctx, units, self.name, policy
            )
            (claim,), (row,) = claims, rows
            running_windows.append(running)
            batches.append((self.name, len(units)))
            readers.append(ctx.reader)
            assert isinstance(ctx.reader, ScopedSourceReader)
            assert ctx.reader.prepared is prepared
            caches.append(_controlled_math_batch(ctx.reader, (self.name, units[0].ref.unit_id)))
            key = self.name, claim.unit_id
            assert key not in original_claims
            original_claims[key] = claim
            if self.name == "normalize.formula":
                with writer.connect() as conn:
                    parents = (
                        conn.execute(
                            text(
                                "SELECT d.dependency_task_id,p.unit_id,p.status,p.input_hash "
                                "FROM ops.task_dependency d JOIN ops.task p "
                                "ON p.id=d.dependency_task_id "
                                "WHERE d.task_id=:task AND d.kind='source_view_interpretation'"
                            ),
                            dict(task=claim.task_id),
                        )
                        .mappings()
                        .all()
                    )
                (parent,) = parents
                expected = original_claims["extract.math", claim.unit_id]
                assert parent["dependency_task_id"] == expected.task_id
                assert parent["unit_id"] == claim.unit_id and parent["status"] == "done"
                assert parent["input_hash"] != "decoy"
                upstream = ctx.reader.source_result(claim.unit_id, "extract.math")
                assert upstream is not None and upstream["input_hash"] != "decoy"
            late = self.name == "extract.math" and claim.unit_id in {
                view.ref.id for view in native_views[4:]
            }
            if late and not reclaim and not decoys:
                ref = units[0].ref
                assert ref.unit_key is not None
                with writer.begin() as conn:
                    decoy = create_task(
                        conn,
                        run_id=RunId(ctx.run.run_id),
                        config_id=row["method_config_id"],
                        stage="extract",
                        unit_type="source_view",
                        unit_id=ref.unit_id,
                        unit_key=ref.unit_key,
                        input_hash="decoy",
                    )
                    (decoy_claim,) = claim_tasks(
                        conn,
                        run_id=RunId(ctx.run.run_id),
                        config_id=row["method_config_id"],
                        holder="scheduler-decoy",
                        limit=1,
                        prepared=prepared,
                    )
                    assert decoy_claim.task_id == decoy
                    complete_unit_result(
                        conn,
                        task_id=decoy,
                        attempt=decoy_claim.attempt,
                        holder="scheduler-decoy",
                        prepared=prepared,
                        result=UnitResult(ref=ref, outcome=ObservationOutcome.EMPTY),
                        method=self,
                        configuration_hash=row["config_hash"],
                        source=ref.unit_key,
                    )
                    decoys.append(decoy)
            if late and reclaim and not reclaimed:
                # Expire only this invocation's exact current claim. A global first
                # running row could belong to another concurrently useful sibling.
                with owner.lock:
                    with admin.begin() as conn:
                        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
                        conn.execute(
                            text(
                                "UPDATE ops.task SET lease_until="
                                "clock_timestamp()-interval '1 second' "
                                "WHERE id=:id"
                            ),
                            dict(id=claim.task_id),
                        )
                    with writer.begin() as conn:
                        (replacement,) = claim_tasks(
                            conn,
                            run_id=RunId(ctx.run.run_id),
                            config_id=row["method_config_id"],
                            holder="source-view-reclaimer",
                            limit=1,
                            prepared=prepared,
                        )
                    assert replacement.task_id == claim.task_id
                    assert replacement.attempt == claim.attempt + 1
                    with pytest.raises(OperationConflict), writer.begin() as conn:
                        complete_task(
                            conn,
                            task_id=claim.task_id,
                            attempt=claim.attempt,
                            holder=claim.holder,
                            prepared=prepared,
                            observations=(),
                            outcome="empty",
                        )
                    with writer.connect() as conn:
                        assert (
                            conn.scalar(
                                text("SELECT count(*) FROM kb.observation WHERE task_id=:task"),
                                dict(task=claim.task_id),
                            )
                            == 0
                        )
                    reclaimed.append((claim, replacement))
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
        method_settings=MethodSettings(
            data_dir=directory, model_cache=directory, execution_policy=policy
        ),
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
    assert max(running_windows) > 1
    assert all(size == 1 for _, size in batches)
    assert len({id(reader) for reader in readers}) == len(readers)
    assert len({id(cache) for cache in caches}) == len(readers)
    assert all(len(cache.native) == 1 for cache in caches)
    caches[0].native.clear()
    assert all(len(cache.native) == 1 for cache in caches[1:])
    assert ready_snapshots and all(len(snapshot) == 4 for snapshot in ready_snapshots)
    first_tasks = [
        original_claims["extract.math", view.ref.id].task_id for view in native_views[:4]
    ]
    with admin.connect() as conn:
        # Exact prior native producer outputs survive either outcome; a useful
        # independent sibling may also settle while a stale failure is drained.
        assert (
            conn.scalar(
                text(
                    "SELECT count(*) FROM kb.observation o JOIN ops.task t ON t.id=o.task_id "
                    "WHERE t.id=ANY(CAST(:prior AS bigint[])) AND t.status='done'"
                ),
                dict(prior=first_tasks),
            )
            == 4
        )
        if reclaim:
            ((victim, replacement),) = reclaimed
            assert (
                conn.scalar(
                    text("SELECT count(*) FROM kb.observation WHERE task_id=:id"),
                    dict(id=victim.task_id),
                )
                == 0
            )
            assert (
                conn.scalar(
                    text("SELECT attempt FROM ops.task WHERE id=:id"), dict(id=victim.task_id)
                )
                == replacement.attempt
            )
        else:
            assert result is not None and len(decoys) == 1
            expected = {
                (method, view.ref.id)
                for method in ("extract.math", "normalize.formula")
                for view in native_views
            }
            assert set(original_claims) == expected
            assert Counter(batches) == {("extract.math", 1): 6, ("normalize.formula", 1): 6}
            dependencies = conn.execute(
                text(
                    "SELECT t.unit_id,d.dependency_task_id FROM ops.task_dependency d "
                    "JOIN ops.task t ON t.id=d.task_id WHERE t.run_id=:run "
                    "AND d.kind='source_view_interpretation'"
                ),
                dict(run=result.run_id),
            ).all()
            assert len(dependencies) == 6
            assert set(dependencies) == {
                (view.ref.id, original_claims["extract.math", view.ref.id].task_id)
                for view in native_views
            }
            assert (
                conn.scalar(
                    text(
                        "SELECT count(*) FROM kb.observation o "
                        "JOIN ops.task t ON t.id=o.task_id WHERE t.run_id=:run"
                    ),
                    dict(run=result.run_id),
                )
                == 12
            )


def test_six_published_views_keep_current_claims_and_native_dependencies(
    commit_db_engine, commit_writer_engine, tmp_path, monkeypatch
):
    _run_source_view_dependency_case(
        commit_db_engine, commit_writer_engine, tmp_path, monkeypatch, reclaim=False
    )


def test_source_view_reclaim_preserves_prior_batch_and_refuses_stale_completion(
    commit_db_engine, commit_writer_engine, tmp_path, monkeypatch
):
    _run_source_view_dependency_case(
        commit_db_engine, commit_writer_engine, tmp_path, monkeypatch, reclaim=True
    )
