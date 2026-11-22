"""Opaque operation code and its explicitly acquired material assets."""

from collections.abc import Callable, Mapping
from functools import lru_cache
from pathlib import Path

from .code_identity import capture_code_identity
from .identity import canonical_bytes
from .types import SourceArtifact


@lru_cache(maxsize=8)
def _producing_code(entries: tuple[Callable, ...]):
    return capture_code_identity(
        Path(__file__).parents[1],
        tuple(dict.fromkeys(entry.__module__ for entry in entries)),
        callables=tuple(entry.__module__ + "." + entry.__qualname__ for entry in entries),
    )


def code_asset_sources(entries: tuple[Callable, ...]):
    """The file observations already retained by this code asset's actual basis."""
    from .python_operation_sources import PythonSource, PythonSourceCollection

    code = _producing_code(entries)
    selected = code.determining_modules if code.complete else code.modules
    root = Path(__file__).parents[1]
    return PythonSourceCollection(
        tuple(
            PythonSource(source.module, source.content, str(root / source.filename))
            for source in selected
        )
    )


def code_asset(
    name: str,
    entries: tuple[Callable, ...],
    assets: tuple[tuple[str, Path], ...] = (),
    *,
    parameters: Mapping[str, object] | None = None,
) -> SourceArtifact:
    code = _producing_code(entries)
    if code.complete:
        from corpus_structure._query_custody import capture_workload_sources

        capture_workload_sources(Path(__file__).resolve().parents[1], code)
    return SourceArtifact(
        name,
        canonical_bytes(
            {
                "profile": "opaque-operation-code-v1",
                "observed_code": code.observed_digest,
                "unknowns": sorted({(item.module, item.reason) for item in code.unknowns}),
                "assets": [(label, path.read_bytes().hex()) for label, path in assets],
                "parameters": parameters,
            }
        ),
        reuse_eligible=code.complete,
    )
