"""Shared immutable value identity for private structural domain products."""

from hashlib import sha256

from pydantic import BaseModel, ConfigDict

from .identity import canonical_bytes


class StructuralValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    @property
    def identity(self) -> str:
        return sha256(canonical_bytes(self.model_dump(mode="json", exclude_none=True))).hexdigest()
