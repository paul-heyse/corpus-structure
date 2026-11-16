"""Current configured-original initialization uses actual admitted source authority."""

import json
from contextlib import contextmanager
from hashlib import sha256
from io import BytesIO

import pypdfium2 as pdfium
from sqlalchemy import select
from typer.testing import CliRunner

from corpus_structure.cli import orchestrate as cli
from corpus_structure.cli.app import app
from corpus_structure.core.evidence import document_key
from corpus_structure.schema import pack
from corpus_structure.semantic.metadata import table
from semantic.current_pdf_source_support import current_pdf_recipe
from semantic.data_operation_kernel_support import Kernel


def test_current_project_init_registers_exact_original_without_activating_or_executing(
    scenario_seeds, tmp_path, monkeypatch
):
    corpus = tmp_path / "corpus"
    (corpus / "toy").mkdir(parents=True)
    document = pdfium.PdfDocument.new()
    page = document.new_page(200, 300)
    page.close()
    output = BytesIO()
    document.save(output)
    document.close()
    original = output.getvalue()
    (corpus / "toy/input.pdf").write_bytes(original)
    domain = tmp_path / "domains/test"
    domain.mkdir(parents=True)
    (domain / "methods.yaml").write_text(
        "configs:\n  ingest.pdf:\n    default:\n      originals: [toy/input.pdf]\n"
    )
    monkeypatch.setattr(pack, "DOMAINS", domain.parent)
    recipe = current_pdf_recipe(tmp_path)
    with scenario_seeds.commit_clone(recipe) as clone:
        kernel = Kernel(clone.admin, clone.stage.preparation, clone.stage.identities, recipe, clone)

        @contextmanager
        def engine(_):
            yield kernel.purpose("write")

        monkeypatch.setattr(cli, "ENGINE", engine)
        response = CliRunner().invoke(
            app,
            [
                "project", "init", "--domain", "test", "--corpus", str(corpus),
                "--name", "configured-originals", "--semantic-release",
                kernel.prepared.release_id, "--json",
            ],
        )
        assert response.exit_code == 0, (response.output, response.exception)
        assert json.loads(response.stdout) == {
            "project": "configured-originals", "release_id": kernel.prepared.release_id,
            "documents": 1,
        }
        with clone.admin.connect() as connection:
            projects = table("data.project")
            project = connection.execute(
                select(projects).where(projects.c.project_id == "configured-originals")
            ).mappings().one()
            assert project["active_release_id"] is None and project["generation"] == 0
            documents = table("kb.document")
            retained = connection.execute(
                select(documents).where(documents.c.project_id == "configured-originals")
            ).mappings().one()
            digest = sha256(original).hexdigest()
            assert retained["key"] == document_key(
                "configured-originals", "toy/input.pdf", digest
            )
            assert retained["content_hash"] == digest and retained["mime"] == "application/pdf"
            assert retained["source_uri"] == "toy/input.pdf"
            assert retained["meta"] == {
                "input_format": "pdf", "source_inventory": "configured-pdf-originals",
            }
            artifacts = table("kb.source_artifact")
            assert connection.scalar(
                select(artifacts.c.content).where(artifacts.c.artifact_digest == digest)
            ) == original
            demands = table("ops.data_demand")
            assert connection.execute(
                select(demands.c.id).where(demands.c.project_id == "configured-originals")
            ).all() == []
