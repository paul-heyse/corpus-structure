"""Typed parent projections over shared GPU hosts; standalone calls own a scope."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from hashlib import sha256
from typing import cast

from pydantic import TypeAdapter

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy

from .gliner import MAX_DIAGNOSTIC_SPANS, GlinerInput, GlinerPack, GlinerRefused, GlinerReport
from .gliner_worker import GlinerAdmission, GlinerWorkerError, _Diagnostic, validate_request
from .native_host import NativeHostGroup, host_request_frame_size, payload_digest
from .native_profiles import (
    NativeProfile,
    NativeSelection,
    gliner_selection,
    preflight_native_runtime,
)


def gliner_host_payload(
    pack, inputs, threshold, overlap_policy, evaluation=False, prepare_only=False
):
    return dict(
        version="gliner-host-1",
        pack=asdict(pack),
        inputs=[asdict(item) for item in inputs],
        threshold=threshold,
        overlap_policy=overlap_policy,
        evaluation=evaluation,
        prepare_only=prepare_only,
    )


class HostedGliner:
    def __init__(self, profile, *, group=None, native_profile=None):
        if profile.device != "cuda":
            raise GlinerRefused("current GLiNER execution requires an explicit CUDA profile")
        self.profile, self._closed = profile, False
        self._owns_group = group is None
        from corpus_structure.settings import NemotronSettings

        self.group = group or NativeHostGroup(
            CharacterizationExecutionPolicy(provider_threads=profile.threads),
            NemotronSettings().endpoint,
        )
        from corpus_structure.semantic.identity import canonical_bytes

        values = asdict(profile)
        values.pop("snapshot")
        matches = [
            s
            for s in self.group._selections.values()
            if s.provider == "gliner"
            and canonical_bytes(s.native.parameters.get("gliner_profile"))
            == canonical_bytes(values)
            and s.native.artifacts == dict(profile.artifact_hashes)
        ]
        self._selection = None
        if native_profile is not None:
            self._selection = NativeSelection(NativeProfile(**native_profile), profile.snapshot)
            if (
                gliner_selection(profile, self._selection.native.runtime_identity).native
                != self._selection.native
            ):
                raise ValueError(
                    "requested analytical profile differs from its frozen native execution"
                )
        elif len(matches) == 1:
            self._selection = matches[0]
        if self._selection is not None:
            self.group.declare((self._selection,))

    @property
    def selection(self):
        if self._selection is None:
            self._selection = gliner_selection(
                self.profile,
                preflight_native_runtime("gliner", self.profile.snapshot)["runtime_identity"],
            )
            self.group.declare((self._selection,))
        return self._selection

    @property
    def closed(self):
        return self._closed

    @property
    def pid(self):
        host = self.group._hosts.get("primary")
        return None if host is None or host._process is None else host._process.pid

    def _exchange(
        self,
        pack,
        inputs,
        *,
        threshold=0.5,
        overlap_policy="flat",
        evaluation=False,
        check_active=None,
        prepare_only=False,
        diagnostic=None,
        receipt_sink=None,
    ):
        if self._closed:
            raise GlinerWorkerError("native GLiNER owner is closed")
        validate_request(
            self.profile,
            pack,
            inputs,
            threshold=threshold,
            overlap_policy=overlap_policy,
            evaluation=evaluation,
        )
        payload = gliner_host_payload(
            pack, inputs, threshold, overlap_policy, evaluation, prepare_only
        )
        if diagnostic is not None:
            payload["diagnostic"] = asdict(diagnostic)
        active = check_active or (lambda: None)
        active()
        from .pm2_worker import Pm2WorkerError, Pm2WorkerRefused

        try:
            host_request_frame_size(
                self.selection,
                payload,
                min(
                    self.group.policy.max_native_request_bytes, self.profile.max_request_frame_bytes
                ),
            )
            response = self.group.infer_result(
                self.selection, payload, active, timeout=self.profile.timeout_seconds
            )
        except Pm2WorkerRefused as error:
            raise GlinerRefused(str(error)) from error
        except Pm2WorkerError as error:
            self._closed = True
            raise GlinerWorkerError(str(error)) from error
        reply = response.payload
        if (
            response.receipt.provider != self.selection.provider
            or response.receipt.profile != self.selection.native.fingerprint
            or response.receipt.runtime != sha256(self.selection.runtime).hexdigest()
            or response.receipt.input_digest != payload_digest(payload)
            or response.receipt.output_digest != payload_digest(reply)
        ):
            raise GlinerWorkerError("native GLiNER receipt differs from admitted exchange")
        decoded = (
            TypeAdapter(tuple[GlinerAdmission, ...]).validate_python(reply["admissions"])
            if prepare_only
            else TypeAdapter(tuple[GlinerReport, ...]).validate_python(reply["reports"])
        )
        if receipt_sink is not None:
            receipt_sink(response.receipt)
        return decoded

    def prepare_members(self, pack, inputs, **kwargs) -> tuple[GlinerAdmission, ...]:
        # _exchange's prepare-only branch decodes exactly this existing DTO.
        return cast(
            tuple[GlinerAdmission, ...], self._exchange(pack, inputs, prepare_only=True, **kwargs)
        )

    def extract(self, pack, inputs, **kwargs) -> tuple[GlinerReport, ...]:
        # Ordinary extraction cannot select the admission-only wire arm.
        return cast(
            tuple[GlinerReport, ...], self._exchange(pack, inputs, prepare_only=False, **kwargs)
        )

    def diagnose(
        self,
        pack: GlinerPack,
        mapping,
        supplied: tuple[tuple[int, int], ...] = (),
        *,
        check_active: Callable[[], None] | None = None,
    ) -> GlinerReport:
        """Observe the ordinary pool and optional source-authorized spans without decoding."""
        from corpus_structure.semantic.source_contexts import ContextRefused

        from .pm2_source import ProviderSpan

        context = mapping.context
        if mapping.provider_text != context.text:
            raise GlinerRefused("GLiNER diagnosis requires the exact selected source text")
        if not isinstance(supplied, tuple) or len(supplied) > MAX_DIAGNOSTIC_SPANS:
            raise GlinerRefused("diagnostic supplied span population exceeds its bound")
        try:
            context.require_native_projection()
            for start, end in supplied:
                if type(start) is not int or type(end) is not int:
                    raise GlinerRefused("supplied spans require integer half-open coordinates")
                mapping.map_extents(
                    (ProviderSpan(start, end, context.text[start:end]),),
                    scope_digest=mapping.scope_digest,
                )
        except ContextRefused as error:
            raise GlinerRefused(str(error)) from error
        (report,) = self._exchange(
            pack,
            (GlinerInput.from_context(context),),
            threshold=0.5,
            overlap_policy="flat",
            evaluation=True,
            check_active=check_active,
            diagnostic=_Diagnostic(mapping.input_digest, supplied),
        )
        return cast(GlinerReport, report)

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
