"""Actual current operation archive inputs for native closure controls."""

from corpus_structure.semantic.releases import persist_release
from semantic.data_operation_kernel_support import STORAGE, prepare_kernel


def archive(engine):
    captured = prepare_kernel(STORAGE)
    bundle, dependencies, profile, prepared = (
        captured.bundle, captured.dependencies, captured.profile, captured.prepared
    )
    with engine.begin() as conn:
        persist_release(conn, bundle, dependencies, profile, prepared)
    return bundle, dependencies, profile, prepared
