"""Actual scheduler leases and shared reader lifetime with controlled method kernels."""

from typing import Literal

from sqlalchemy import text

from corpus_structure.core.method import Digest, MethodSettings, Resources, UnitResult
from corpus_structure.core.vocab import ObservationOutcome, Stage, TaskUnitType
from corpus_structure.methods.math.methods import ExtractMathConfig, NormalizeFormulaConfig
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.semantic.operations import OperationBinding, register_document

from .operation_scenario_support import prepare_operation_scenario


def test_ready_methods_claim_only_current_batch_and_keep_group_reader(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    # Native task/dependency mechanics and real owned reads are exercised here; the
    # controlled kernels establish scheduler behavior, not mathematical extraction.
    class IndependentNormalize(NormalizeFormulaConfig):
        source_dependencies: Literal[None] = None

    prepared = prepare_operation_scenario(semantic_db_engine, observations=True, evaluation=True)
    with semantic_writer_engine.begin() as conn:
        for number in range(6):
            path = tmp_path / f"input-{number}.pdf"
            original = f"%PDF-1.7\nindependent source {number}".encode()
            path.write_bytes(original)
            register_document(
                conn, project_id="p", source_uri=path.name, original_path=str(path),
                original=original, mime="application/pdf",
            )
    batches, readers, preparations = [], [], []

    class ControlledMath:
        version = "jit-control-1"
        tier = "deterministic"
        confidence_source = None
        unit_type = TaskUnitType.DOCUMENT
        resources = Resources(batch_size=4)

        def __init__(self, name, family, config):
            self.name, self.family, self.Config = name, family, config

        def select(self, run, config):
            return run.reader.documents(tuple(f"input-{number}.pdf" for number in range(6)))

        def input_digest(self, unit, config):
            return Digest(f"independent:{unit.ref.unit_key}".encode())

        def run(self, units, config, ctx):
            with semantic_writer_engine.connect() as conn:
                running = conn.execute(text(
                    "SELECT m.name,t.id FROM ops.task t JOIN ops.method_config c "
                    "ON c.id=t.method_config_id JOIN ops.method m ON m.id=c.method_id "
                    "WHERE t.run_id=:run AND t.status='running'"
                ), {"run": ctx.run.run_id}).all()
            assert len(running) == len(units) <= 4
            assert {row.name for row in running} == {self.name}
            batches.append((self.name, len(units)))
            readers.append(ctx.reader)
            batch = ctx.reader.math_readings_batch
            batch.bind(ctx.reader)
            preparations.append(batch)
            for unit in units:
                assert ctx.reader.original(unit.ref.unit_id).startswith(b"%PDF-")
            return tuple(UnitResult(ref=unit.ref, outcome=ObservationOutcome.EMPTY) for unit in units)

    registry = MethodRegistry(
        [ControlledMath("extract.math", "extract", ExtractMathConfig),
         ControlledMath("normalize.formula", "normalize", IndependentNormalize)],
        MethodsFile(configs={"extract.math": {"default": {}}, "normalize.formula": {"default": {}}},
                    sections={"math": {}}),
    )
    result = run_source_methods(
        semantic_writer_engine, project_id="p", prepared=prepared,
        binding=OperationBinding(prepared.release_id, "z", 0, b"{}"), registry=registry,
        graph=Graph(((Stage.EXTRACT, (Step("extract.math/default"), Step("normalize.formula/default"))),)),
        method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
    )
    assert batches == [("extract.math", 4), ("extract.math", 2),
                       ("normalize.formula", 4), ("normalize.formula", 2)]
    assert all(reader is readers[0] for reader in readers)
    assert all(batch is preparations[0] for batch in preparations)
    assert result.status == "source_ready"
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM ops.task WHERE run_id=:run AND status='empty'"),
                           {"run": result.run_id}) == 12
