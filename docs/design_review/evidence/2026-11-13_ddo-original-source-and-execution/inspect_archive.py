"""Diagnose the actual target archive that exceeded PostgreSQL's JSONB value bound.

Run with uv run python <this-file>. Uses only the controlled original-source target
fixture; performs no database access or publication and prints no source/body data.
"""

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "python/corpus-structure"))

from corpus_structure.semantic.releases import _archive_bytes, _products  # noqa: E402
from tests.semantic.test_data_operation_original_native import original_target  # noqa: E402

with TemporaryDirectory(prefix="ddo-archive-diagnostic-") as temporary:
    bundle, dependencies, profile, prepared = original_target.__wrapped__(Path(temporary))
    products = _products(prepared)
    report = {
        "release": prepared.release_id,
        "archive_bytes": len(_archive_bytes(bundle, dependencies, prepared)),
        "product_sections": {
            name: len(json.dumps(value, separators=(",", ":")).encode())
            for name, value in products.items()
        },
        "largest_artifacts": sorted(
            ((item.kind, len(item.content)) for item in prepared.artifacts),
            key=lambda row: row[1], reverse=True,
        )[:10],
        "largest_registry_rows": sorted(
            ((item.kind, item.name, len(item.body)) for item in prepared.registry_rows),
            key=lambda row: row[2], reverse=True,
        )[:10],
        "dependency_bytes": sum(len(item.content) for item in dependencies.artifacts),
    }
    print(json.dumps(report, indent=2))
