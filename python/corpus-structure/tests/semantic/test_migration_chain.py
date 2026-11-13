"""Deferred authoring binds executable registered bytes without deploying them."""

from hashlib import sha256

import pytest

from corpus_structure.semantic.migration_chain import (
    frozen_base_location,
    registered_base,
    verify_registered_base,
)
from corpus_structure.semantic.refusals import SemanticRefusal


def _chain(tmp_path):
    versions = tmp_path / "versions"
    versions.mkdir()
    (tmp_path / "env.py").write_text("# environment\n")
    (versions / "base.py").write_text("revision='base'\ndown_revision=None\n")
    fields = ["revision='next'", "down_revision='base'"]
    for kind in ("UPGRADE", "STATE", "ADMISSION"):
        name, content = kind.lower() + ".txt", (kind + "\n").encode()
        (versions / name).write_bytes(content)
        fields.extend((
            f"NATIVE_{kind}_FILE={name!r}",
            f"NATIVE_{kind}_SHA256={sha256(content).hexdigest()!r}",
        ))
    (versions / "next.py").write_text("\n".join(fields))
    return registered_base(tmp_path, "base", "next")


def test_registered_chain_freezes_bytes_and_refuses_drift(tmp_path):
    base = _chain(tmp_path)
    assert base.revisions == ("next",)
    with frozen_base_location(tmp_path, base) as copied:
        assert (copied / "versions/upgrade.txt").read_bytes() == b"UPGRADE\n"
        (tmp_path / "versions/upgrade.txt").write_bytes(b"changed")
        assert (copied / "versions/upgrade.txt").read_bytes() == b"UPGRADE\n"
    with pytest.raises(SemanticRefusal, match="artifact differs"):
        verify_registered_base(tmp_path, base)


@pytest.mark.parametrize("change", ["env", "wrapper", "branch", "cycle", "missing", "duplicate"])
def test_registered_chain_refuses_unreviewed_metadata(tmp_path, change):
    base = _chain(tmp_path)
    path = tmp_path / "versions/next.py"
    if change == "env":
        (tmp_path / "env.py").write_text("# changed\n")
    elif change == "wrapper":
        path.write_text(path.read_text() + "\n# changed wrapper")
    elif change == "branch":
        path.write_text(path.read_text() + "\ndepends_on='base'")
    elif change == "cycle":
        path.write_text(path.read_text().replace("down_revision='base'", "down_revision='next'"))
    elif change == "missing":
        path.unlink()
    else:
        (tmp_path / "versions/duplicate.py").write_bytes(path.read_bytes())
    with pytest.raises(SemanticRefusal):
        verify_registered_base(tmp_path, base)


def test_author_successor_on_undeployed_base_rolls_back(semantic_database_at, native_settings):
    from sqlalchemy.engine import make_url

    from corpus_structure.cli.schema import author_native_candidate
    from corpus_structure.semantic import migrations

    predecessor = "semantic_bep_located_v2"
    target = migrations.head_revision()
    assert target is not None and target != predecessor
    with semantic_database_at(predecessor) as engine:
        source = make_url(native_settings.database.url).set(database=engine.url.database)
        maintenance = make_url(native_settings.database.maintenance_url).set(
            database=engine.url.database
        )
        settings = native_settings.model_copy(update={
            "database": native_settings.database.model_copy(update={
            "url": source.render_as_string(hide_password=False),
            "maintenance_url": maintenance.render_as_string(hide_password=False),
            })
        })
        base = registered_base(migrations.ALEMBIC_DIR, predecessor, target)
        report, products = author_native_candidate(
            settings, None, None, expected_predecessor=target, native_base=base
        )
        assert report.predecessor == target
        assert products["native_operations.json"]
        with engine.begin() as connection:
            assert migrations.current_revision(connection) == predecessor
        with pytest.raises(SemanticRefusal, match="base differs"):
            author_native_candidate(
                settings, None, None, expected_predecessor=predecessor, native_base=base
            )
        with engine.begin() as connection:
            assert migrations.current_revision(connection) == predecessor
