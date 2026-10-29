"""New semantic target: explicit preparation, separate from the selected installed projection."""

from .identity import fact_key, occurrence_key
from .prepare import prepare_release
from .types import (
    Diagnostic,
    PreparationError,
    PreparationProfile,
    PreparedRelease,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
    VocabularyMember,
    VocabularySnapshot,
)

__all__ = [
    "Diagnostic",
    "PreparationError",
    "PreparationProfile",
    "PreparedRelease",
    "ResolvedDependencies",
    "SourceArtifact",
    "SourceBundle",
    "VocabularyMember",
    "VocabularySnapshot",
    "fact_key",
    "occurrence_key",
    "prepare_release",
]
