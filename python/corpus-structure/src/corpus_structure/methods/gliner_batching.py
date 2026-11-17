"""Ordered GLiNER input chunks admitted by the actual profile and host encoder."""

from .gliner import GlinerRefused
from .gliner_worker import validate_request
from .native_host import host_request_frame_size
from .native_host_clients import gliner_host_payload
from .native_profiles import NativeProfile, NativeSelection, gliner_selection
from .pm2_worker import Pm2WorkerRefused


def gliner_input_batches(profile, pack, inputs, *, threshold, overlap_policy, native_profile=None):
    """Yield (original ordinals, singleton refusal), retaining every input once.

    This performs no model preparation. Runtime identity changes the fixed-width
    profile hash, never the envelope's byte length. Pure callers without a native
    selection use that same header shape solely for frame admission.
    """
    selection = (
        NativeSelection(NativeProfile(**native_profile), profile.snapshot)
        if native_profile is not None
        else gliner_selection(profile, {})
    )

    def admit(ordinals):
        members = tuple(inputs[index] for index in ordinals)
        validate_request(
            profile, pack, members, threshold=threshold, overlap_policy=overlap_policy
        )
        host_request_frame_size(
            selection,
            gliner_host_payload(pack, members, threshold, overlap_policy),
            profile.max_request_frame_bytes,
        )

    pending = ()
    for index in range(len(inputs)):
        candidate = (*pending, index)
        try:
            admit(candidate)
        except (GlinerRefused, Pm2WorkerRefused):
            if pending:
                yield pending, None
                pending = ()
            try:
                admit((index,))
            except (GlinerRefused, Pm2WorkerRefused) as error:
                yield (index,), str(error)
            else:
                pending = (index,)
        else:
            pending = candidate
    if pending:
        yield pending, None
