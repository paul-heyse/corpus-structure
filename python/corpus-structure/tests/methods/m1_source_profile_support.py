"""Controlled inputs and builders shared by the m1 source profile consumers."""

from corpus_structure.methods import m1_source


def config(tmp_path, **changes):
    return m1_source.M1Config(
        snapshot=tmp_path,
        checkpoint="fixture",
        revision="immutable",
        artifact_hashes=tuple(
            (name, "a" * 64)
            for name in (
                "config.json",
                "encoder_config/config.json",
                "model.safetensors",
                "tokenizer.json",
                "tokenizer_config.json",
            )
        ),
        **changes,
    )
