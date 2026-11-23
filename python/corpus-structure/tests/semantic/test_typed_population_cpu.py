"""Actual typed CPU input custody under the ordinary prepared-work owner."""

import importlib
import inspect
import json
import os
from concurrent.futures import Future
from types import SimpleNamespace

import pytest

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.core.work import drive_prepared_work
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.cpu_execution import CPUExecutionScope, CPUReply, CPURequestCancelled
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.data_operation_cpu import (
    PopulationCPUInput,
    plan_cpu_call,
    prepared_cpu_descriptor,
)
from corpus_structure.semantic.data_operation_population import population_layout
from corpus_structure.semantic.population_ipc import SealedPopulationIpc
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.types import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)

_SCHEMA = b"""
id: urn:typed-cpu
name: typed_cpu
prefixes:
  p: 'urn:typed-cpu:'
  xsd: 'http://www.w3.org/2001/XMLSchema#'
default_prefix: p
default_range: string
types:
  string: {base: str, uri: 'xsd:string'}
  integer: {base: int, uri: 'xsd:integer'}
classes:
  Item:
    attributes:
      ordinal: {range: integer, required: true, minimum_value: 0, maximum_value: 100}
      label: {required: true}
  Population:
    attributes:
      rows:
        range: Item
        multivalued: true
        inlined: true
        required: true
        annotations:
          'cs:collection': '{"unit":"partitioned","partition_key":"block","item_order":["ordinal"],"address":["ordinal"],"field_groups":{"label":["label"]}}'
"""


@pytest.fixture(scope="module")
def prepared_population():
    prepared = prepare_release(
        SourceBundle("typed_cpu", (SourceArtifact("typed_cpu", _SCHEMA),)),
        data_operation_dependencies(ResolvedDependencies()),
        PreparationProfile(version="semantic-2"),
    )
    model = bound_data_operation_model(prepared)
    kind = next(kind for kind in model.kinds if kind.name == "Population")
    layout = population_layout(prepared, kind, "rows")
    return prepared, layout.from_rows([{"ordinal": 0, "label": "café"}])


def test_spawned_population_argument_retains_credit_through_parent_verification(
    prepared_population, tmp_path, monkeypatch
):
    prepared, population = prepared_population
    population = population.project_groups(("label",))
    path = tmp_path / "typed_population_worker_fixture.py"
    source = b"""\
from corpus_structure.semantic.data_operation_population import AcquiredPopulation

def observe(rows: tuple[AcquiredPopulation, ...], check_active) -> list[list[str]]:
    check_active()
    assert all(item.table.column_names == ['label'] for item in rows)
    return [item.table.column('label').to_pylist() for item in rows]
"""
    path.write_bytes(source)
    monkeypatch.syspath_prepend(str(tmp_path))
    name = path.stem
    observe = importlib.import_module(name).observe
    descriptor = prepared_cpu_descriptor(((name, str(path), source),), name + ".observe", None, ())
    signature = inspect.signature(observe)
    calls = []

    with pytest.MonkeyPatch.context() as patch:
        write = SealedPopulationIpc.write

        def bounded_write(*args, **kwargs):
            assert cpu.budget.used_bytes - cpu.preparation_bytes == (
                cpu.policy.max_packet_bytes + cpu.policy.max_reply_bytes
            )
            return write(*args, **kwargs)

        patch.setattr(SealedPopulationIpc, "write", staticmethod(bounded_write))
        cpu = CPUExecutionScope(
            prepared, CharacterizationExecutionPolicy(workers=1, max_submissions=1)
        )

        def verify():
            calls.append(cpu.budget.used_bytes - cpu.preparation_bytes)
            assert any(permit.reserved == calls[-1] for permit in cpu._admissions.values())

        try:
            reply = drive_prepared_work(
                plan_cpu_call(
                    descriptor,
                    signature.bind((population, population), lambda: None),
                    signature,
                    verify=verify,
                    execution_owner=SimpleNamespace(cpu=cpu, reservation=None),
                    check_active=lambda: None,
                    population_inputs={
                        "rows": (
                            PopulationCPUInput(population, "projection-a", "content-a"),
                            PopulationCPUInput(population, "projection-a", "content-a"),
                        )
                    },
                ),
                lambda: None,
            )
            assert json.loads(reply.content) == [["café"], ["café"]]
            assert reply.pid != os.getpid() and reply.main_thread
            assert calls == [cpu.policy.max_packet_bytes + cpu.policy.max_reply_bytes] * 2
            assert cpu.budget.used_bytes == cpu.preparation_bytes
        finally:
            cpu.close()
    assert cpu.budget.used_bytes == 0


def test_population_descriptor_offer_can_retire_before_the_child_receives(prepared_population):
    from multiprocessing import resource_sharer

    _, population = prepared_population
    options = dict(
        schema=population.layout.schema, request_digest="request", projection_digest="projection"
    )
    with SealedPopulationIpc.write(population.table, max_bytes=16384, **options) as payload:
        offered = payload.offer()
        _, key = offered.duplicate._id
        resource = vars(resource_sharer)["_resource_sharer"]
        assert key in resource._cache
        offered.retire()
        assert key not in resource._cache
        with payload.open(max_bytes=16384, **options) as acquired:
            assert acquired.equals(population.table, check_metadata=True)
        extent = payload.byte_length
    with pytest.raises(ValueError, match="byte bound"):
        SealedPopulationIpc.write(population.table, max_bytes=extent - 1, **options)


def test_cancelled_population_keeps_attached_capacity_until_work_settles(
    prepared_population, monkeypatch
):
    prepared, population = prepared_population
    cpu = CPUExecutionScope(prepared, retain_schema=False)
    try:
        future = Future()
        assert future.set_running_or_notify_cancel()
        monkeypatch.setattr(cpu._executor(), "submit", lambda *args: future)
        permit = cpu.try_admit()
        assert permit is not None
        handle = cpu.submit_closed_python(permit, b"{}", populations=((population, "scope"),))
        ((owned, _),) = permit.population_files
        descriptor = owned._descriptor
        assert descriptor is not None
        amount = permit.reserved
        handle.cancel()
        assert not handle.retire()
        assert cpu.budget.used_bytes == amount
        assert os.fstat(descriptor).st_size == owned.byte_length
        future.set_result(CPUReply(handle.digest, b"{}", -1, True))
        with pytest.raises(CPURequestCancelled):
            handle.collect()
        assert handle.retire()
        assert cpu.budget.used_bytes == 0
        with pytest.raises(OSError):
            os.fstat(descriptor)
    finally:
        cpu.close()
