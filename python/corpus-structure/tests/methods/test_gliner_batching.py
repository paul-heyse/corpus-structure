"""Pure physical packet admission; these controls make no provider claim."""

from dataclasses import replace

from corpus_structure.methods.gliner import (
    CUDA_WHITESPACE_PROFILE,
    GlinerInput,
    GlinerPack,
    GlinerProfile,
)
from corpus_structure.methods.gliner_batching import gliner_input_batches
from corpus_structure.methods.native_host import host_request_frame_size
from corpus_structure.methods.native_host_clients import gliner_host_payload
from corpus_structure.methods.native_profiles import gliner_selection


def profile(tmp_path, **options):
    return GlinerProfile(
        tmp_path,
        "fixture",
        "immutable",
        tuple(
            (name, "a" * 64)
            for name in (
                "config.json",
                "encoder_config/config.json",
                "model.safetensors",
                "tokenizer.json",
                "tokenizer_config.json",
            )
        ),
        version=CUDA_WHITESPACE_PROFILE,
        **options,
    )


def batches(selected, pack, inputs):
    return tuple(gliner_input_batches(selected, pack, inputs, threshold=0.5, overlap_policy="flat"))


def test_batch_chunks_preserve_population_and_exact_utf8_host_frame_boundary(tmp_path):
    selected = profile(tmp_path)
    pack = GlinerPack("controlled", '{"entities":["term"]}')
    inputs = tuple(
        GlinerInput(f"context:{index}", str(index) * 64, "é" * 200) for index in range(6)
    )
    assert batches(selected, pack, inputs) == (((0, 1, 2, 3), None), ((4, 5), None))
    pair_bytes = host_request_frame_size(
        gliner_selection(selected, {}),
        gliner_host_payload(pack, inputs[:2], 0.5, "flat"),
        selected.max_request_frame_bytes,
    )
    exact = replace(selected, max_request_frame_bytes=pair_bytes)
    assert batches(exact, pack, inputs[:3]) == (((0, 1), None), ((2,), None))
    smaller = replace(selected, max_request_frame_bytes=pair_bytes - 1)
    assert batches(smaller, pack, inputs[:3]) == (((0,), None), ((1,), None), ((2,), None))


def test_oversized_member_refuses_only_itself_and_duplicate_identity_splits(tmp_path):
    selected = profile(tmp_path, max_batch_bytes=16)
    pack = GlinerPack("controlled", '{"entities":["term"]}')
    first = GlinerInput("same", "a" * 64, "short")
    too_big = GlinerInput("large", "b" * 64, "é" * 9)
    result = batches(selected, pack, (first, too_big, first))
    assert result[0] == ((0,), None) and result[2] == ((2,), None)
    assert result[1][0] == (1,) and result[1][1] == "live input byte bound exceeded"
    assert batches(selected, pack, (first, first)) == (((0,), None), ((1,), None))
