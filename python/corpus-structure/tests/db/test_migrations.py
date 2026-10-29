"""Alembic linked to the model (P0-M-4): an unregistered revision is refused, applications kept."""

from __future__ import annotations

import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

from corpus_structure.core._model import revision
from corpus_structure.core.db import migrations

ALEMBIC = Path(__file__).resolve().parents[2] / "alembic"


def test_a_revision_for_an_unregistered_model_revision_is_refused(tmp_path: Path) -> None:
    hook = migrations.refusing_unregistered()
    hook(None, None, [])  # the installed revision is logged
    with pytest.raises(migrations.UnregisteredModelRevision, match=r"is not in revisions\.yaml"):
        migrations.refusing_unregistered(current="f" * 64)(None, None, [])
    empty = tmp_path / "revisions.yaml"
    empty.write_text("[]\n", encoding="utf-8")
    with pytest.raises(migrations.UnregisteredModelRevision):
        migrations.refusing_unregistered(empty)(None, None, [])
    assert issubclass(migrations.UnregisteredModelRevision, Exception)


def test_a_revision_file_states_its_model_revision(tmp_path: Path) -> None:
    location = tmp_path / "alembic"
    shutil.copytree(ALEMBIC, location, ignore=shutil.ignore_patterns("__pycache__"))
    config = Config()
    config.set_main_option("script_location", str(location))
    args = migrations.template_args()
    script = ScriptDirectory.from_config(config).generate_revision(
        "9999", "seeded", model_revision=args["model_revision"], model_label=args["model_label"]
    )
    assert script is not None
    text = Path(script.path).read_text(encoding="utf-8")
    assert f"model_revision: str = {revision.CONTENT_HASH!r}" in text


def test_applied_steps_are_recorded() -> None:
    module = SimpleNamespace(model_revision=revision.CONTENT_HASH)
    revision_map = SimpleNamespace(get_revision=lambda rev: SimpleNamespace(module=module))
    step = SimpleNamespace(
        up_revision_id="0001", is_upgrade=True, is_stamp=False, revision_map=revision_map
    )
    config = SimpleNamespace(attributes={})
    ctx = SimpleNamespace(environment_context=SimpleNamespace(config=config))
    migrations.on_version_apply(ctx, step, {"0001"}, {})
    assert config.attributes["applied"] == [
        {
            "revision": "0001",
            "direction": "upgrade",
            "stamp": False,
            "model_revision": revision.CONTENT_HASH,
        }
    ]
    kwargs = migrations.configure_kwargs()
    assert set(kwargs) == {"template_args", "process_revision_directives", "on_version_apply"}
