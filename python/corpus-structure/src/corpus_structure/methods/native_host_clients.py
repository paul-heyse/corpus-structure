"""Typed parent projections over shared GPU hosts; standalone calls own a scope."""

from __future__ import annotations

from dataclasses import asdict

from pydantic import TypeAdapter

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy

from .gliner import GlinerReport
from .gliner_worker import GlinerAdmission, GlinerWorker, validate_request
from .native_host import NativeHostGroup, host_request_frame_size
from .native_profiles import gliner_selection, preflight_native_runtime


def gliner_host_payload(pack, inputs, threshold, overlap_policy, evaluation=False, prepare_only=False):
    return dict(version="gliner-host-1", pack=asdict(pack), inputs=[asdict(item) for item in inputs], threshold=threshold, overlap_policy=overlap_policy, evaluation=evaluation, prepare_only=prepare_only)


class HostedGliner:
    def __init__(self, profile, *, group=None):
        self.profile, self._closed = profile, False
        self._owns_group = group is None
        self.group = group or NativeHostGroup(CharacterizationExecutionPolicy(provider_threads=profile.threads))
        from corpus_structure.semantic.identity import canonical_bytes
        values = asdict(profile)
        values.pop("snapshot")
        matches = [s for s in self.group._selections.values() if s.provider == "gliner" and canonical_bytes(s.native.parameters.get("gliner_profile")) == canonical_bytes(values) and s.native.artifacts == dict(profile.artifact_hashes)]
        self.selection = matches[0] if len(matches) == 1 else gliner_selection(profile, preflight_native_runtime("gliner", profile.snapshot)["runtime_identity"])
        self.group.declare((self.selection,))

    @property
    def closed(self):
        return self._closed

    @property
    def pid(self):
        host = self.group._hosts.get("primary")
        return None if host is None or host._process is None else host._process.pid

    def _exchange(self, pack, inputs, *, threshold=0.5, overlap_policy="flat", evaluation=False, check_active=None, prepare_only=False, diagnostic=None):
        if self._closed:
            raise ValueError("native GLiNER owner is closed")
        validate_request(self.profile, pack, inputs, threshold=threshold, overlap_policy=overlap_policy, evaluation=evaluation)
        payload = gliner_host_payload(pack, inputs, threshold, overlap_policy, evaluation, prepare_only)
        if diagnostic is not None:
            payload["diagnostic"] = asdict(diagnostic)
        host_request_frame_size(self.selection, payload, min(self.group.policy.max_native_request_bytes, self.profile.max_request_frame_bytes))
        reply = self.group.infer(self.selection, payload, check_active or (lambda: None), timeout=self.profile.timeout_seconds)
        if prepare_only:
            return TypeAdapter(tuple[GlinerAdmission, ...]).validate_python(reply["admissions"])
        return TypeAdapter(tuple[GlinerReport, ...]).validate_python(reply["reports"])

    def prepare_members(self, pack, inputs, **kwargs):
        return self._exchange(pack, inputs, prepare_only=True, **kwargs)

    def extract(self, pack, inputs, **kwargs):
        return self._exchange(pack, inputs, **kwargs)

    def diagnose(self, *args, **kwargs):
        return GlinerWorker.diagnose(self, *args, **kwargs)

    def close(self):
        self._closed = True
        if self._owns_group:
            self.group.close()


class HostedPM2:
    """A claim-scoped borrower; closing it never kills useful group siblings."""
    def __init__(self, selection, group, check_active):
        self.selection, self.group = selection, group
        self.startup = group.startup(selection, check_active)
        self._closed = False

    @property
    def closed(self):
        host = self.group._hosts.get(self.selection.native.host)
        return self._closed or (host is not None and host.closed)

    def infer(self, payload, *, check_active):
        return self.group.infer(self.selection, payload, check_active)

    def close(self):
        self._closed = True
