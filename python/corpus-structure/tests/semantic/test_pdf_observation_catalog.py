"""Failed-source diagnostics are discoverable without inference or selected Docling content."""

import base64
import json
from hashlib import sha256

import pytest
from pydantic import ValidationError
from sqlalchemy import insert
from typer.testing import CliRunner

from corpus_structure.cli.app import app
from corpus_structure.cli.output import CliState
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import complete_task
from corpus_structure.semantic.pdf_storage import PdfObservationListRequest, read_pdf_observations
from corpus_structure.settings import Settings
from semantic.pdf_integration_support import HOLDER, RESPONSE, observation, prepare, publish
from semantic.pdf_integration_support import native_source as native_source
from semantic.pdf_integration_support import pdf13_db as pdf13_db


@pytest.mark.parametrize(
    "changes",
    [
        {"limit": 0},
        {"limit": 1001},
        {"run_id": 0},
        {"task_id": 0},
        {"kind": "native"},
    ],
)
def test_observation_catalog_requires_typed_bounded_scope(changes):
    with pytest.raises(ValidationError):
        PdfObservationListRequest.model_validate({"run_id": 1, "task_id": 2, **changes})


def test_failed_task_observations_are_paged_and_inspectable(pdf13_db, commit_reader_engine):
    db = pdf13_db
    request = PdfObservationListRequest(run_id=db.job.run, task_id=db.job.task, limit=1)
    with (
        commit_reader_engine.connect() as conn,
        pytest.raises(ValueError, match="finished source task"),
    ):
        read_pdf_observations(conn, request)

    failed = observation(db.source, key="pass-c-failed", pass_role="C", outcome="failed")
    failed["occurrences"] = []
    failed["coverage"][0]["outcome"] = "unknown"
    failed["observation"]["diagnostic"] = "controlled response parser failure"
    retained = prepare(failed, db.source)
    publish(db, retained)
    with db.writer.begin() as conn:
        complete_task(
            conn,
            task_id=db.job.task,
            attempt=db.job.attempt,
            holder=HOLDER,
            prepared=db.prepared,
            observations=[],
            outcome="failed",
            error={"code": "controlled-parser-failure", "message": "retained raw response"},
        )
    expected = {
        "pass-a": db.observations[0].digest,
        "pass-b": db.observations[1].digest,
        "pass-c-failed": retained.digest,
    }
    with commit_reader_engine.connect() as conn:
        first = read_pdf_observations(conn, request)
        assert [pin.product_key for pin in first.products] == ["pass-a"]
        assert first.next_cursor is not None
        second = read_pdf_observations(
            conn, request.model_copy(update={"cursor": first.next_cursor, "limit": 2})
        )
        assert second.next_cursor is None
        assert {
            pin.product_key: pin.content_digest for pin in (*first.products, *second.products)
        } == expected
        assert all(pin.kind == "recognition_observation" for pin in second.products)
        assert read_pdf_observations(conn, request) == first
        for bad_cursor in ("not-base64", base64.urlsafe_b64encode(b"{}").decode()):
            with pytest.raises(ValueError, match="continuation"):
                read_pdf_observations(conn, request.model_copy(update={"cursor": bad_cursor}))

    other = db.create(name="other-source-task")
    with db.writer.begin() as conn:
        complete_task(
            conn,
            task_id=other.task,
            attempt=other.attempt,
            holder=HOLDER,
            prepared=db.prepared,
            observations=[],
            outcome="failed",
            error={"code": "controlled-source-failure"},
        )
    with db.admin.begin() as conn:
        conn.execute(insert(table("data.project")).values(project_id="foreign"))
        conn.execute(
            insert(table("data.realization")).values(
                project_id="foreign", realization_id="foreign-z", release_id=db.prepared.release_id
            )
        )
    foreign = db.create(project="foreign", name="foreign-source")
    with commit_reader_engine.connect() as conn:
        for changes in (
            {"run_id": other.run},
            {"task_id": other.task},
            {"run_id": foreign.run},
            {"task_id": foreign.task},
            {"task_id": 99999999},
        ):
            with pytest.raises(ValueError, match="requested run/project"):
                read_pdf_observations(conn, request.model_copy(update=changes))
        with pytest.raises(ValueError, match="continuation"):
            read_pdf_observations(
                conn,
                PdfObservationListRequest(
                    run_id=other.run,
                    task_id=other.task,
                    cursor=first.next_cursor,
                ),
            )

    settings = Settings(
        database={
            "url": db.admin.url.set(
                drivername="postgresql", username="corpus_sem_writer"
            ).render_as_string(hide_password=False)
        }
    )
    cli = CliRunner()

    def invoke(*args):
        result = cli.invoke(
            app, ["source", *args, "--json"], obj=CliState(settings_factory=lambda: settings)
        )
        assert result.exit_code == 0, (result.output, result.exception)
        return json.loads(result.stdout)

    default = invoke("native-products", str(db.job.run))
    assert [row["product_key"] for row in default] == ["native"]
    page = invoke(
        "native-products",
        str(db.job.run),
        "--observations",
        "--task",
        str(db.job.task),
        "--limit",
        "1",
    )
    assert page["products"][0]["kind"] == "recognition_observation"
    tail = invoke(
        "native-products",
        str(db.job.run),
        "--observations",
        "--task",
        str(db.job.task),
        "--cursor",
        page["next_cursor"],
        "--limit",
        "2",
    )
    failed_pin = tail["products"][-1]
    assert failed_pin == {
        "kind": "recognition_observation",
        "task_id": db.job.task,
        "product_key": "pass-c-failed",
        "content_digest": retained.digest,
    }
    pin_args = (
        str(db.job.run),
        "--producing-task",
        str(failed_pin["task_id"]),
        "--product",
        failed_pin["product_key"],
        "--native-digest",
        failed_pin["content_digest"],
    )
    companion = invoke("inspect", *pin_args, "--native-view", "companion")
    assert companion["rows"][0]["descriptor"]["observation"]["outcome"] == "failed"
    assert (
        companion["rows"][0]["descriptor"]["observation"]["diagnostic"]
        == "controlled response parser failure"
    )
    artifact = invoke(
        "inspect",
        *pin_args,
        "--native-view",
        "artifact",
        "--artifact-digest",
        sha256(RESPONSE).hexdigest(),
    )
    assert base64.b64decode(artifact["rows"][0]["data"]) == RESPONSE
    assert artifact["rows"][0]["encoding"] == "base64"
    for args in (
        ("--observations",),
        ("--task", str(db.job.task)),
        ("--observations", "--task", str(db.job.task), "--limit", "1001"),
        ("--observations", "--task", str(foreign.task)),
    ):
        refused = cli.invoke(
            app,
            ["source", "native-products", str(db.job.run), *args, "--json"],
            obj=CliState(settings_factory=lambda: settings),
        )
        assert refused.exit_code != 0
