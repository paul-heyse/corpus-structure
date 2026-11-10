"""Exercise actual retained schema routes with controlled publication/prepare defects."""

from __future__ import annotations

import json
import platform
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from typer.testing import CliRunner

from corpus_structure.cli.app import app
from corpus_structure.cli.managed import ResultStore


def invoke(root: Path, *args: str):
    return CliRunner().invoke(
        app,
        list(args),
        env={"CORPUS_CI_RESULTS": str(root), "COLUMNS": "100", "NO_COLOR": "1"},
    )


def manifest(root: Path):
    (item,) = ResultStore(root).list(None, 2, None).results
    return item


def summary(result, item):
    return {
        "exit_code": result.exit_code,
        "exception_type": type(result.exception).__name__ if result.exception else None,
        "managed_outcome": item.outcome,
        "artifact_roles": sorted(item.artifacts),
        "observation_journal_registered": item.observations is not None,
    }


def main() -> int:
    with TemporaryDirectory(prefix="cld-schema-boundary-") as temporary:
        base = Path(temporary)
        control = invoke(base / "control", "schema", "check", "--retain-diagnostics", "--json")
        control_item = manifest(base / "control")
        control_summary = summary(control, control_item)
        control_summary["has_compile_result"] = bool(
            control.exit_code == 0 and json.loads(control.stdout).get("execution_model_id")
        )

        with patch(
            "corpus_structure.cli.diagnostic_artifacts.publish_diagnostic",
            side_effect=OSError("controlled optional publication failure"),
        ):
            publication = invoke(
                base / "publication", "schema", "check", "--retain-diagnostics", "--json"
            )
        publication_summary = summary(publication, manifest(base / "publication"))
        publication_summary["has_compile_result"] = bool(
            publication.exit_code == 0 and json.loads(publication.stdout).get("execution_model_id")
        )

        group = ExceptionGroup("controlled schema defect", [RuntimeError("controlled child")])
        group.add_note("controlled group note")
        group.__cause__ = ValueError("controlled cause")
        with patch("corpus_structure.semantic.regeneration.prepare_release", side_effect=group):
            unexpected = invoke(
                base / "unexpected", "schema", "check", "--retain-diagnostics", "--json"
            )
        unexpected_item = manifest(base / "unexpected")
        unexpected_summary = summary(unexpected, unexpected_item)
        unexpected_summary["original_exception_preserved"] = unexpected.exception is group
        replay = invoke(
            base / "unexpected", "schema", "diagnostic", unexpected_item.id, "--json"
        )
        unexpected_summary["diagnostic_read_exit_code"] = replay.exit_code
        if replay.exit_code == 0:
            document = json.loads(replay.stdout)
            unexpected_summary["retained_validation_categories"] = sorted(
                {row["category"] for row in document["report"]["observations"]}
            )
            unexpected_summary["retained_report_version"] = document["report"]["report_version"]
        checks = {
            "control_succeeds": control.exit_code == 0 and control_summary["has_compile_result"],
            "optional_publication_preserves_success": publication.exit_code == 0
            and publication_summary["has_compile_result"],
            "unexpected_defect_has_distinct_retained_observations": unexpected_item.observations
            is not None
            and "diagnostic-report" not in unexpected_item.artifacts,
        }
        print(
            json.dumps(
                {
                    "python": platform.python_version(),
                    "versions": {name: version(name) for name in ("typer", "rich", "structlog")},
                    "control": control_summary,
                    "optional_publication_failure": publication_summary,
                    "unexpected_group": unexpected_summary,
                    "contract_checks": checks,
                },
                indent=2,
            )
        )
        return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
