"""Invocation-owned verified preparation and bounded regional immutable inputs.

Only the full execution loader constructs this context. Historical archive hydration
never confers execution admission; each native operation retains its live checks.
"""

from __future__ import annotations

import json
from concurrent.futures import Future
from contextlib import contextmanager
from hashlib import sha256
from types import MappingProxyType

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy

from .identity import canonical_bytes

_VERIFIED = object()


def _immutable(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _immutable(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_immutable(item) for item in value)
    return value


class VerifiedExecutionPreparation:
    def __init__(
        self, prepared, *, policy: CharacterizationExecutionPolicy | None = None, _authority
    ):
        if _authority is not _VERIFIED:
            raise ValueError("execution preparation requires full release verification")
        from .cpu_execution import CPUExecutionScope

        self.prepared = prepared
        self.cpu = CPUExecutionScope(prepared, policy)
        self.policy = self.cpu.policy
        from corpus_structure.methods.characterization_resources import ProviderExecution

        self.providers = ProviderExecution(self.cpu.budget, self.cpu.policy)
        self._closed = False
        self._method_closers = {}

    def register_methods(self, registry):
        for method in registry.methods():
            closer = getattr(method, "close", None)
            if closer is not None:
                self._method_closers[id(method)] = closer

    def require_release(self, release_id):
        if self._closed or self.prepared.release_id != release_id:
            raise ValueError("execution preparation is closed or belongs to another release")
        return self.prepared

    def __enter__(self):
        self.require_release(self.prepared.release_id)
        return self

    def __exit__(self, *exc):
        self._closed = True
        from contextlib import ExitStack

        with ExitStack() as closers:
            closers.callback(self.cpu.close)
            closers.callback(self.providers.close)
            for closer in self._method_closers.values():
                closers.callback(closer)


def prepare_execution(conn, release_id, *, policy: CharacterizationExecutionPolicy | None = None):
    from .releases import load_release

    return VerifiedExecutionPreparation(
        load_release(conn, release_id), policy=policy, _authority=_VERIFIED
    )


class _ReadCapacityUnavailable(ValueError):
    """A synchronous read must yield before opening its next payload."""


class _ReadResult:
    def __init__(self, value):
        self.future = Future()
        self.future.set_result(value)

    def collect(self):
        return self.future.result()

    def cancel(self):
        pass

    def retire(self):
        return True


class RegionalPreparation:
    """Canonical owned values shared by independently connection-bound stage readers.

    Source working objects are reconstructed per reader, preserving mutable analytical
    caches locally. Layer reads retain native run authorization even on a cache hit.
    """

    def __init__(self, execution):
        self.execution = execution
        self._sources = {}
        self._layers = {}
        self._validated = {}
        self._decoded = {}
        self._release_owners = {}
        self._reserved = 0
        self._read_credit = None
        self._closed = False

    def _require_open(self):
        if self._closed:
            raise ValueError("regional preparation is closed")

    def _retain_size(self, size):
        self._require_open()
        self.execution.cpu.budget.reserve(size)
        self._reserved += size

    def _read_bound(self, contract):
        from .cpu_execution import CapacityExceeded

        bound = min(contract, self.execution.cpu.budget.limit - self._reserved)
        if bound < 1:
            raise CapacityExceeded("retained region leaves no capacity for another read")
        return bound

    @contextmanager
    def _read_window(self, bound):
        from .cpu_execution import CapacityExceeded

        self._require_open()
        budget = self.execution.cpu.budget
        if bound > budget.limit:
            raise CapacityExceeded("one complete read exceeds the owned byte policy")
        try:
            budget.reserve(bound)
        except CapacityExceeded as error:
            raise _ReadCapacityUnavailable(str(error)) from error
        previous = self._read_credit
        credit = [bound]
        self._read_credit = credit
        try:
            yield
        finally:
            self._read_credit = previous
            budget.release(credit[0])

    def read_work(self, read):
        """Retry only pre-hydration capacity waits, after the read snapshot closes.

        The callable owns its connection/transaction. Successful cache entries remain
        charged to this region; no partial payload is returned on a capacity wait.
        """
        from corpus_structure.core.work import PreparedWork

        def try_read():
            try:
                return _ReadResult(read())
            except _ReadCapacityUnavailable:
                return None

        return PreparedWork(try_read)

    def _retain(self, content):
        size = len(content)
        if self._read_credit is None:
            self._retain_size(size)
        else:
            if size > self._read_credit[0]:
                from .cpu_execution import CapacityExceeded

                raise CapacityExceeded("canonical read exceeds its admitted byte window")
            self._read_credit[0] -= size
            self._reserved += size
        return content

    def source_view(self, conn, reference, *, analysis, prepared, read_budget=None):
        self._require_open()
        from .source_views import load_source_view

        self.execution.require_release(prepared.release_id)
        identity = reference if isinstance(reference, int) else reference.id
        key = (identity, prepared.release_id)
        if key not in self._sources:
            from .pdf_record_reader import PublishedReadBudget

            bound = self._read_bound(min(256 * 1024**2, self.execution.cpu.policy.max_packet_bytes))
            if read_budget is not None and read_budget.max_bytes > bound:
                from .cpu_execution import CapacityExceeded

                raise CapacityExceeded("source read budget exceeds its admitted byte window")
            bounded_budget = read_budget or PublishedReadBudget(bound, bound)
            with self._read_window(bound):
                source = load_source_view(
                    conn,
                    identity,
                    analysis=False,
                    analysis_context=prepared,
                    read_budget=bounded_budget,
                )
                if not isinstance(reference, int) and source.ref != reference:
                    raise ValueError("regional source differs from the admitted source pin")
                body = canonical_bytes(
                    dict(
                        text=source.text,
                        pieces=source.pieces,
                        items=source.items,
                        ancestors=source.ancestors,
                        health=source.health,
                        integrated_context=source.integrated_context,
                    )
                )
                self._sources[key] = (source.ref, source.text_policy, self._retain(body))
        ref, policy, content = self._sources[key]
        if not isinstance(reference, int) and ref != reference:
            raise ValueError("regional source differs from the admitted source pin")
        if analysis:
            from .analysis_contracts import prepare_text_policy

            policy = prepare_text_policy(prepared)
        value = json.loads(content)
        from .source_views import PreparedSourceView

        return PreparedSourceView(
            ref,
            value["text"],
            tuple(value["pieces"]),
            tuple(value["items"]),
            tuple(value["ancestors"]),
            value["health"],
            policy,
            analysis,
            value["integrated_context"],
        )

    def layer(self, conn, reference, *, run_id):
        self._require_open()
        from .characterization_store import read_layer, read_layer_manifest

        # Native manifest admission checks the current run/source/permissions. The
        # exact pin authenticates cached immutable bytes, not arbitrary caller input.
        if reference in self._layers:
            bound = self._read_bound(8 * 1024**2)
            with self._read_window(bound):
                read_layer_manifest(conn, reference, run_id=run_id, max_bytes=bound)
        else:
            bound = self._read_bound(64 * 1024**2)
            with self._read_window(bound):
                report = read_layer(conn, reference, run_id=run_id, max_bytes=bound)
                self.retain_native_layer(reference, report)
        return self._layers[reference]

    def retain_native_layer(self, reference, report):
        """Retain exact authenticated canonical bytes once across regional consumers."""
        self._require_open()
        if report.reference(reference.task_id) != reference:
            raise ValueError("regional layer differs from its exact published pin")
        if reference in self._layers:
            cached = self._layers[reference]
            if cached.content != report.content:
                raise ValueError("regional layer differs from retained canonical content")
            return cached
        self._retain(report.content)
        self._layers[reference] = report
        return report

    def primary_layers(self, conn, run_id, source_view_id, references):
        """Admit a bounded native page before reading; retain complete selected layers.

        Native authorization still runs for every selection, including cache hits. The
        temporary credit covers a live page while its canonical bodies enter the cache;
        accumulated bodies stay charged until this region's final consumer releases them.
        """
        self._require_open()
        from .characterization_store import read_primary_layers

        bound = self._read_bound(min(256 * 1024**2, self.execution.cpu.policy.max_packet_bytes))
        budget = self.execution.cpu.budget
        budget.reserve(bound)
        try:
            return read_primary_layers(
                conn,
                run_id,
                source_view_id,
                references,
                max_bytes=bound,
                retain=self.retain_native_layer,
            )
        finally:
            budget.release(bound)

    def validate_layer(self, prepared, payload, *, dependencies, releases):
        self._require_open()
        from .characterization import _LayerValidation, _require_layer_contract
        from .product_reference import ProductReference

        if payload.get("release_id") != prepared.release_id:
            raise ValueError("characterization layer uses another semantic release")

        def body_of(report):
            digest = report.content_digest
            if digest not in self._decoded:
                # Decoded immutable views have their own encoded-state reservation.
                self._retain(report.content)
                self._decoded[digest] = _immutable(report.payload)
            return self._decoded[digest]

        fingerprints = {}
        visiting = set()

        def premises(report):
            digest = report.content_digest
            if digest in visiting:
                raise ValueError("layer dependency cycle")
            if digest in fingerprints:
                return fingerprints[digest]
            visiting.add(digest)
            try:
                body = body_of(report)
                _require_layer_contract(body)
                release = releases.get(body["release_id"])
                if release is None:
                    raise ValueError("layer requires its own archived semantic release")
                # Keep participating owners alive for the scoped object-identity
                # premise; archive-cache eviction cannot recycle its identity.
                self._release_owners[id(release)] = release
                closure = []
                for value in body.get("dependencies", ()):
                    pin = ProductReference(**value)
                    dependency = dependencies.get(pin)
                    if dependency is None or dependency.reference(pin.task_id) != pin:
                        raise ValueError("layer requires exact dependency closure")
                    closure.append((pin.values(), premises(dependency)))
                key = sha256(canonical_bytes((id(release), digest, closure))).hexdigest()
                fingerprints[digest] = key
                return key
            finally:
                visiting.remove(digest)

        # Cached proofs apply only to exact transitive bytes and released contracts.
        # Newly authored roots are deliberately never seeded into this validator.
        reusable = {}
        for report in dependencies.values():
            key = premises(report)
            if key in self._validated:
                reusable[report.content_digest] = self._validated[key]

        reusable.pop(sha256(canonical_bytes(payload)).hexdigest(), None)
        validator = _LayerValidation(prepared, releases, dependencies)
        validator.validated.update(reusable)
        result = validator.validate(payload)
        for report in validator.validated.values():
            key = premises(report)
            if key not in self._validated:
                self._retain_size(len(report.content) + len(key))
                self._validated[key] = report
        return result

    def close(self):
        self._sources.clear()
        self._layers.clear()
        self._validated.clear()
        self._decoded.clear()
        self._release_owners.clear()
        self.execution.cpu.budget.release(self._reserved)
        self._reserved = 0
        self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
