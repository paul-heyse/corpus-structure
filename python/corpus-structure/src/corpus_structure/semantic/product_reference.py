"""Qualified immutable product identity shared by PDF producers and consumers."""
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True, slots=True)
class ProductReference:
    """Immutable product identity, separate from its source rendition/content identity."""

    task_id: int
    product_key: str
    content_digest: str

    def __post_init__(self) -> None:
        if isinstance(self.task_id, bool) or self.task_id < 1 or not self.product_key:
            raise ValueError("product reference requires a producing task and product key")
        if len(self.content_digest) != 64 or any(
            c not in "0123456789abcdef" for c in self.content_digest
        ):
            raise ValueError("product reference requires its SHA-256 content digest")

    def values(self) -> dict[str, Any]:
        return dict(
            task_id=self.task_id, product_key=self.product_key, content_digest=self.content_digest
        )

