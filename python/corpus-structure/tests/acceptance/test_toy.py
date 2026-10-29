"""C4: the same production journey on an independently declared second domain."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy import text

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.values import NumberValue
from corpus_structure.intervene.server import build_server
from corpus_structure.intervene.service import Session
from corpus_structure.intervene.testing import submit_batches
from corpus_structure.orchestrate import phase0, project
from corpus_structure.orchestrate.testing import run_to_completion
from corpus_structure.serve.journey import coverage, serve_query
from corpus_structure.serve.protocol import Scope
from corpus_structure.serve.queries import GENERIC
from corpus_structure.serve.registry import build_registry
from corpus_structure.serve.results import ClaimAnswer

REPO = Path(__file__).resolve().parents[4]

# Packs are loaded from their files, not installed Python packages. Give the checker the same
# concrete row class while runtime uses the production plug-in import route.
if TYPE_CHECKING:
    from domains.toy.queries import OwnershipRow
else:
    OwnershipRow = build_registry(pack=REPO / "domains/toy")["ownership_at"].result


def test_toy_pack_journey(committing_db: Any, tmp_path: Path) -> None:
    pack = REPO / "domains/toy"
    with committing_db.begin() as conn:
        project.init_project(
            conn,
            domain="toy",
            corpus=REPO / "fixtures/toy/corpus",
            registry=phase0.registry(pack),
            name="toy",
        )
    url = committing_db.url.set(drivername="postgresql").render_as_string(hide_password=False)
    options = dict(
        url=url,
        project_name="toy",
        slice="toy",
        method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
    )
    # Start with exactly one organization in the reference run. A same-name alias must
    # not replace the later organizations' distinct registry identities.
    baseline_options = {**options, "slice": "one_owner"}
    baseline = run_to_completion(committing_db, **baseline_options)
    ownership = json.loads((REPO / "fixtures/toy/ownership.json").read_text())
    baseline_submission = submit_batches(
        build_server(Session(committing_db)),
        baseline.run_id,
        {ownership["unit_key"]: (ownership["batch"], ownership["frame"])},
    )
    assert all(result.status == "done" for result in baseline_submission.values())
    reference = run_to_completion(committing_db, **baseline_options)
    assert reference.status == "finished"
    # A test fixture promotion selects the reference for the next run; no operator
    # promotion workflow or scoring qualification is claimed by this test.
    with committing_db.begin() as conn:
        conn.execute(
            text("UPDATE meta.project SET promoted_run_id=:r WHERE name='toy'"),
            {"r": reference.run_id},
        )
    first = run_to_completion(committing_db, **options)
    assert first.status == "finished"
    fixtures = [
        json.loads((REPO / "fixtures/toy" / f"{name}.json").read_text())
        for name in ("ownership", "registers")
    ]
    batches = {f["unit_key"]: (f["batch"], f["frame"]) for f in fixtures}
    with committing_db.connect() as conn:
        initial = coverage(conn, first.run_id, Scope.of_units(tuple(batches)))
        assert initial.unresolved == 2
    submitted = submit_batches(build_server(Session(committing_db)), first.run_id, batches)
    assert len(submitted) == 2
    for result in submitted.values():
        assert result.status == "done", result
        assert not result.rejected and not result.dropped and not result.findings
    with committing_db.connect() as conn:
        assert coverage(conn, first.run_id, Scope.of_units(tuple(batches))) == initial
    second = run_to_completion(committing_db, **options)
    assert second.status == "finished"
    queries = build_registry(GENERIC, pack)
    with committing_db.connect() as conn:
        kinds = set(
            conn.execute(
                text("SELECT kind FROM kb.entity WHERE run_id=:r AND kind IS NOT NULL"),
                {"r": second.run_id},
            ).scalars()
        )
        assert {"toy:clause", "toy:notice"} <= kinds
        organizations = conn.execute(
            text(
                "SELECT e.key, i.value_text FROM kb.entity e "
                "JOIN kb.entity_identity i ON i.entity_id=e.id "
                "WHERE e.run_id=:r AND e.type='toy:Organization' AND i.slot='toy:registry_id'"
            ),
            {"r": second.run_id},
        ).all()
        assert {row[1] for row in organizations} == {"ORG-101", "ORG-202", "org-101"}
        assert len({row[0] for row in organizations}) == 3
        all_claims = serve_query(
            conn,
            queries,
            "claims",
            {"predicate": "toy:owns", "include_candidates": True},
            run=second.run_id,
            max_chars=1_000_000,
        )
        claims = [ClaimAnswer.model_validate(row) for row in all_claims.rows]
        assert len(claims) == 9, [(row.modality, row.status, row.qualifiers) for row in claims]
        reports = [row for row in claims if row.modality == "toy:reported"]
        assert len(reports) == 2
        assert all(row.attribution is not None for row in reports)
        assert len({row.attribution.key for row in reports if row.attribution is not None}) == 2
        ambiguous = [row for row in claims if row.status == "ambiguous"]
        assert len(ambiguous) == 2
        shares = [NumberValue.model_validate(row.qualifiers["toy:share"]) for row in ambiguous]
        assert {share.v for share in shares} == {"0.5", "0.8"}
        filing = [row for row in claims if "toy:filing_ref" in row.qualifiers]
        assert len(filing) == 1
        assert all(row.evidence for row in claims)
        result = serve_query(
            conn,
            queries,
            "ownership_at",
            {"asset": "P-17", "date": "2020-07-01"},
            run=second.run_id,
            max_chars=1_000_000,
        )
        ownership = [OwnershipRow.model_validate(row) for row in result.rows]
        intervals = [row for row in ownership if row.interval is not None]
        assert {row.applicability for row in intervals} == {"established", "not_applicable"}
        assert any(row.applicability == "unknown" for row in ownership)
        assert result.coverage.extracted == 2 and not result.coverage.partial
        # The notice has a stored kind but never receives an extraction task.
        task_keys = (
            conn.execute(
                text("SELECT unit_key FROM ops.task WHERE run_id=:r AND stage='propose'"),
                {"r": second.run_id},
            )
            .scalars()
            .all()
        )
        assert not any("notice" in key for key in task_keys)


def test_toy_profile_unknown_kind_refuses_run_start(
    committing_db: Any,
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    import pytest

    from corpus_structure.ingest import profile
    from corpus_structure.orchestrate import runs

    pack = REPO / "domains/toy"
    with committing_db.begin() as conn:
        project.init_project(
            conn,
            domain="toy",
            corpus=REPO / "fixtures/toy/corpus",
            registry=phase0.registry(pack),
            name="toy-invalid-kind",
        )
    original = profile.load_profile

    def invalid(name: Any, *args: Any, **kwargs: Any) -> Any:
        loaded = original(name, *args, **kwargs)
        return loaded.model_copy(
            update={
                "block_hints": (
                    loaded.block_hints[0].model_copy(update={"statement_kind": "toy:missing"}),
                )
            }
        )

    monkeypatch.setattr(profile, "load_profile", invalid)
    url = committing_db.url.set(drivername="postgresql").render_as_string(hide_password=False)
    with pytest.raises(runs.ProfileRefused, match="toy:missing"):
        run_to_completion(
            committing_db,
            url=url,
            project_name="toy-invalid-kind",
            slice="toy",
            method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
        )
    with committing_db.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM ops.run")).scalar_one() == 0
