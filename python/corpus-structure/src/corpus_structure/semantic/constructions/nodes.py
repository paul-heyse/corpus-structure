"""Common immutable references and identities for factorized symbolic products."""

from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from corpus_structure.semantic.identity import canonical_bytes


@dataclass(frozen=True)
class Reference:
    target: str | None = None
    choice_group: str | None = None

    def edge(self, role: str, order: int = 0) -> dict[str, Any]:
        return dict(
            role=role,
            order=order,
            structural=True,
            **({"target": self.target} if self.target else {"choice_group": self.choice_group}),
        )


def identity(kind: str, value: Any) -> str:
    return kind + ":" + sha256(canonical_bytes(value)).hexdigest()
