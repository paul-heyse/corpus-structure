"""Input-dependent encoder responses for controlled alignment claims."""

from math import hypot
from types import SimpleNamespace


def controlled_vector(text):
    """Use the character-position sum as the first axis of a unit vector."""
    coordinate = sum((index + 1) * ord(character) for index, character in enumerate(text))
    norm = hypot(coordinate, 1)
    return coordinate / norm, 1 / norm


def controlled_encoder(observe, *, invalid_vector=False, physical_error=False):
    def encode(texts, **options):
        observe(tuple(texts), options)
        if physical_error:
            raise RuntimeError("controlled native model failure")
        return [
            (2.0, 0.0) if invalid_vector and index == 1 else controlled_vector(text)
            for index, text in enumerate(texts)
        ]

    return SimpleNamespace(
        tokenizer=SimpleNamespace(encode=lambda text, **options: tuple(text)),
        encode_document=encode,
        encode_query=encode,
    )
