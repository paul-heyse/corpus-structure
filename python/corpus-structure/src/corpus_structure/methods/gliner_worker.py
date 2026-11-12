"""GLiNER admission contracts and the shared CUDA host entry point.

Historical CPU profiles remain data; there is no current CPU worker dispatcher.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .gliner import GlinerRefused

if TYPE_CHECKING:
    from .native_host_clients import HostedGliner


class GlinerWorkerError(RuntimeError):
    """An admitted native GPU operation failed."""


@dataclass(frozen=True)
class _Diagnostic:
    source_map_digest: str
    supplied: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class GlinerAdmission:
    ordinal: int
    context_id: str
    context_digest: str
    admitted: bool
    reason: str | None = None


def validate_request(profile, pack, inputs, *, threshold, overlap_policy, evaluation=False):
    if not isinstance(inputs, tuple) or not inputs or len(inputs) > profile.max_batch:
        raise GlinerRefused("batch must be a nonempty bounded immutable tuple")
    # Decoding policy belongs to the requesting operation. Private language
    # characterization needs overlapping cues without claiming evaluation custody.
    supported_overlap = {"flat", "nested", "allow"}
    if not 0 <= threshold <= 1 or overlap_policy not in supported_overlap:
        raise GlinerRefused("unsupported threshold or overlap policy")
    sizes = [len(item.text.encode()) for item in inputs]
    if max(sizes) > profile.max_input_bytes or sum(sizes) > profile.max_batch_bytes:
        raise GlinerRefused("live input byte bound exceeded")
    if len(pack.declaration_json.encode()) > profile.max_schema_bytes:
        raise GlinerRefused("schema byte bound exceeded")
    metadata = [
        pack.release,
        pack.version,
        overlap_policy,
        *(value for item in inputs for value in (item.context_id, item.context_digest)),
    ]
    if sum(len(value.encode()) for value in metadata) > profile.max_metadata_bytes:
        raise GlinerRefused("request metadata byte bound exceeded")
    if len({item.context_id for item in inputs}) != len(inputs):
        raise GlinerRefused("batch context identities must be distinct")


def GlinerWorker(profile) -> HostedGliner:
    from .native_host_clients import HostedGliner

    if profile.device != "cuda":
        raise GlinerRefused(
            "historical CPU profiles are read-only; current GLiNER execution requires CUDA"
        )
    return HostedGliner(profile)
