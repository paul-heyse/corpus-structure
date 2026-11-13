"""Process snapshots and the bounded, process-wide override cache lifetime."""

from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from threading import Barrier, Lock, get_ident

import pytest

from corpus_structure.methods.math import grammar
from corpus_structure.semantic import analysis_contracts, contracts
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.runtime_bindings import (
    runtime_fingerprint,
    runtime_implementation_digests,
)
from corpus_structure.semantic.types import RegistryRow


def changed_snapshot(installed, suffix):
    analysis = tuple(
        replace(item, content=item.content + suffix) if item.name == "libraries.json" else item
        for item in installed.analysis_inputs
    )
    return contracts.ImplementationSnapshot(
        replace(
            installed.execution_inputs,
            implementations=contracts.semantic_implementation_inputs(analysis),
        ),
        analysis,
    )


def composed_release(inputs):
    model = contracts.compile_execution_model(inputs)
    base = prepare_release(inputs.schema)
    return replace(
        base,
        execution_model_id=model.model_id,
        registry_rows=(
            *base.registry_rows,
            RegistryRow("execution_model", model.model_id, model.content),
        ),
    )


def test_repeated_contexts_and_parses_acquire_one_process_snapshot(monkeypatch):
    acquire = contracts._acquire_implementation
    acquisitions = []

    def counted():
        acquisitions.append(1)
        return acquire()

    monkeypatch.setattr(contracts, "_acquire_implementation", counted)
    monkeypatch.setattr(grammar, "_STANDALONE_CONTEXTS", OrderedDict())
    monkeypatch.setattr(grammar, "_MEMO", OrderedDict())
    contracts._reset_installed_implementation()
    try:
        for _ in range(3):
            analysis_contracts.prepare_interpretation_context(macros={})
        prepared = composed_release(contracts.trusted_execution_inputs())
        for _ in range(3):
            analysis_contracts.prepare_interpretation_context(prepared, macros={})
        for source in ("x+1", "x+1", "x+2"):
            assert grammar.parse(source).tree is not None
        assert acquisitions == [1]
        snapshot = contracts.current_implementation()
        assert contracts.analysis_implementation_inputs() is snapshot.analysis_inputs
        assert contracts.trusted_execution_inputs() is snapshot.execution_inputs
        assert snapshot.runtime_digests == runtime_implementation_digests(snapshot.analysis_inputs)
        assert snapshot.standalone_runtime_fingerprint == runtime_fingerprint(
            snapshot.analysis_inputs
        )
        with pytest.raises(FrozenInstanceError):
            setattr(snapshot, "analysis_inputs", ())  # noqa: B010 - exercise frozen runtime enforcement
    finally:
        contracts._reset_installed_implementation()


def test_concurrent_cold_first_use_acquires_one_shared_snapshot(monkeypatch):
    acquire = contracts._acquire_implementation
    acquisitions = []
    attempts = []
    both_cold = Barrier(2)
    initialization = Lock()

    class ColdLock:
        def __enter__(self):
            attempts.append(get_ident())
            assert len(attempts) <= 2, "warm snapshot reads must avoid the initialization lock"
            # Both consumers have observed the empty slot before either can acquire it.
            both_cold.wait(timeout=10)
            initialization.acquire()

        def __exit__(self, *_args):
            initialization.release()

    def counted():
        acquisitions.append(1)
        return acquire()

    contracts._reset_installed_implementation()
    try:
        with monkeypatch.context() as patch:
            patch.setattr(contracts, "_implementation_lock", ColdLock())
            patch.setattr(contracts, "_acquire_implementation", counted)
            with ThreadPoolExecutor(max_workers=2) as workers:
                first = workers.submit(contracts.current_implementation)
                second = workers.submit(contracts.current_implementation)
                snapshot = first.result(timeout=60)
                assert second.result(timeout=60) is snapshot
            assert len(set(attempts)) == 2
            assert acquisitions == [1]
            assert contracts.current_implementation() is snapshot
            assert contracts.current_implementation() is snapshot
            assert len(attempts) == 2
    finally:
        contracts._reset_installed_implementation()


def test_nested_exceptional_overrides_bypass_ambient_caches_and_restore_warm_entries(monkeypatch):
    installed = contracts.current_implementation()
    outer = changed_snapshot(installed, b"\n")
    inner = changed_snapshot(installed, b"\n\n")
    monkeypatch.setattr(grammar, "_STANDALONE_CONTEXTS", OrderedDict())
    monkeypatch.setattr(grammar, "_MEMO", OrderedDict())
    monkeypatch.setattr(grammar, "MEMO_SIZE", 2)
    calls = dict(boundary=0, context=0, read=0)
    for owner, attribute, name in (
        (analysis_contracts, "_prepare_boundary", "boundary"),
        (grammar, "_prepare_standalone_context", "context"),
        (grammar, "_read", "read"),
    ):
        original = getattr(owner, attribute)

        def counted(*args, _original=original, _name=name, **kwargs):
            calls[_name] += 1
            return _original(*args, **kwargs)

        monkeypatch.setattr(owner, attribute, counted)
    analysis_contracts._boundary_cached.cache_clear()
    try:
        warm_boundary = analysis_contracts._boundary()
        first = grammar.parse("x+1")
        grammar.parse("x+2")
        warm_context = grammar._standalone_context({}, "any_value")
        warm_results = tuple(grammar._MEMO.items())
        warm_contexts = tuple(grammar._STANDALONE_CONTEXTS.items())
        baseline = calls.copy()
        assert grammar.parse("x+1") is first
        # Preserve this warm LRU order, too: override hits must not move entries.
        warm_results = tuple(grammar._MEMO.items())

        class LeaveScope(Exception):
            pass

        with pytest.raises(LeaveScope), contracts.implementation_override(outer):
            assert contracts.implementation_overridden()
            assert contracts.current_implementation() is outer
            with ThreadPoolExecutor(max_workers=1) as worker:
                assert worker.submit(contracts.current_implementation).result() is outer
                worker.submit(analysis_contracts._boundary).result()
            scoped = grammar.parse("x+1")
            assert scoped is not first
            assert scoped.context.key() == warm_context.key()
            assert grammar.parse("x+1", context=warm_context) is not first
            with pytest.raises(LeaveScope), contracts.implementation_override(inner):
                assert contracts.current_implementation() is inner
                grammar.parse("x+3")
                analysis_contracts._boundary()
                raise LeaveScope
            assert contracts.current_implementation() is outer
            with contracts.implementation_override(contracts.IMPLEMENTATION_UNAVAILABLE):
                assert contracts.implementation_overridden()
                with pytest.raises(RuntimeError, match="acquisition is forbidden"):
                    grammar.parse("x+1")
                with pytest.raises(RuntimeError, match="acquisition is forbidden"):
                    analysis_contracts._boundary()
                # Explicit contexts still parse, but cannot hit or write the ordinary memo.
                assert grammar.parse("x+1", context=warm_context) is not first
            assert contracts.current_implementation() is outer
            raise LeaveScope

        assert contracts.current_implementation() is installed
        assert not contracts.implementation_overridden()
        assert tuple(grammar._MEMO.items()) == warm_results
        assert tuple(grammar._STANDALONE_CONTEXTS.items()) == warm_contexts
        assert calls == dict(
            boundary=baseline["boundary"] + 5,
            context=baseline["context"] + 3,
            read=baseline["read"] + 4,
        )
        after_override = calls.copy()
        assert analysis_contracts._boundary() is warm_boundary
        assert grammar._standalone_context({}, "any_value") is warm_context
        assert grammar.parse("x+1") is first
        assert calls == after_override
    finally:
        analysis_contracts._boundary_cached.cache_clear()


def test_snapshot_refuses_inconsistent_semantic_primaries():
    installed = contracts.current_implementation()
    changed = changed_snapshot(installed, b"\n")
    assert changed.semantic_digests != installed.semantic_digests
    assert changed.standalone_runtime_fingerprint != installed.standalone_runtime_fingerprint
    assert changed.semantic_digests == tuple(
        (item.name, item.digest) for item in changed.execution_inputs.implementations
    )
    with pytest.raises(ValueError, match="semantic implementation inputs differ"):
        contracts.ImplementationSnapshot(installed.execution_inputs, changed.analysis_inputs)


def test_explicit_physical_sources_never_consult_the_process_snapshot():
    from importlib.resources import files

    from corpus_structure.schema.physical import PHYSICAL_ROOT, physical_source_closure

    root = files("corpus_structure").joinpath("model", "semantic")
    sources = physical_source_closure(PHYSICAL_ROOT, lambda name: root.joinpath(name).read_bytes())
    with contracts.implementation_override(contracts.IMPLEMENTATION_UNAVAILABLE):
        analysis = contracts.analysis_implementation_inputs(physical_sources=sources)
        execution = contracts.trusted_execution_inputs(physical_sources=sources)
        assert execution.implementations == contracts.semantic_implementation_inputs(analysis)
        assert contracts.compile_execution_model(execution).analysis_profiles
