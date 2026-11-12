"""Invocation-owned verified preparation and bounded regional immutable inputs.

Only the full execution loader constructs this context. Historical archive hydration
never confers execution admission; each native operation retains its live checks.
"""

from __future__ import annotations

import json
from hashlib import sha256
from types import MappingProxyType

from .identity import canonical_bytes

_VERIFIED = object()


def _immutable(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _immutable(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_immutable(item) for item in value)
    return value


class VerifiedExecutionPreparation:
    def __init__(self, prepared, *, _authority):
        if _authority is not _VERIFIED:
            raise ValueError("execution preparation requires full release verification")
        from .cpu_execution import CPUExecutionScope

        self.prepared = prepared
        self.cpu = CPUExecutionScope(prepared)
        self._closed = False

    def require_release(self, release_id):
        if self._closed or self.prepared.release_id != release_id:
            raise ValueError("execution preparation is closed or belongs to another release")
        return self.prepared

    def __enter__(self):
        self.require_release(self.prepared.release_id)
        return self

    def __exit__(self, *exc):
        self._closed = True
        self.cpu.close()


def prepare_execution(conn, release_id):
    from .releases import load_release

    return VerifiedExecutionPreparation(load_release(conn, release_id), _authority=_VERIFIED)


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
        self._closed = False

    def _require_open(self):
        if self._closed:
            raise ValueError("regional preparation is closed")

    def _retain_size(self, size):
        self._require_open()
        self.execution.cpu.budget.reserve(size)
        self._reserved += size

    def _retain(self, content):
        self._retain_size(len(content))
        return content

    def source_view(self, conn, reference, *, analysis, prepared, read_budget=None):
        self._require_open()
        from .source_views import load_source_view

        self.execution.require_release(prepared.release_id)
        key = (reference, prepared.release_id)
        if key not in self._sources:
            source = load_source_view(
                conn,
                reference.id,
                analysis=False,
                analysis_context=prepared,
                read_budget=read_budget,
            )
            if source.ref != reference:
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
            read_layer_manifest(conn, reference, run_id=run_id)
        else:
            report = read_layer(conn, reference, run_id=run_id)
            self._retain(report.content)
            self._layers[reference] = report
        return self._layers[reference]

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
