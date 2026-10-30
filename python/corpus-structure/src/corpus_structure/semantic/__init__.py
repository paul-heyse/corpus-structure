"""New semantic target: explicit preparation, separate from the selected installed projection."""

from .composed import composed_dependencies
from .identity import fact_key, occurrence_key
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
    "composed_dependencies",
    "fact_key",
    "occurrence_key",
    "prepare_release",
]


_DEFAULT_DEPENDENCIES = ResolvedDependencies()
_DEFAULT_PROFILE = PreparationProfile()


def prepare_release(
    bundle: SourceBundle,
    dependencies: ResolvedDependencies = _DEFAULT_DEPENDENCIES,
    profile: PreparationProfile = _DEFAULT_PROFILE,
) -> PreparedRelease:
    """Acquire the compiler only for explicit preparation, not package imports."""
    from .prepare import prepare_release as prepare

    return prepare(bundle, dependencies, profile)
