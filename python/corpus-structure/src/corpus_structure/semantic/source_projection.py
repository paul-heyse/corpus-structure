"""Stable native source-statement identity shared by current publication consumers."""

from hashlib import sha256

from .identity import canonical_bytes


def statement_identity(
    release_id: str, realization_id: str, rendition_key: str, locator: str
) -> str:
    return (
        "entity:"
        + sha256(
            canonical_bytes(
                [release_id, realization_id, "source-statement", rendition_key, locator]
            )
        ).hexdigest()
    )
