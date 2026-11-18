"""Declared deployment-key boundaries on independent source trees."""

import os
import runpy
import shutil
import subprocess
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from native_deployment_key import deployment_key


@pytest.fixture
def source_tree(tmp_path):
    package = tmp_path / "src" / "corpus_structure"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (package / "selected.py").write_text("from . import transitive\n")
    (package / "transitive.py").write_text("VALUE = 1\n")
    (package / "unrelated.py").write_text("VALUE = 1\n")
    chain = tmp_path / "chain"
    chain.mkdir()
    (chain / "revision.py").write_text("from corpus_structure import selected\n")
    (chain / "state.json").write_text('{"large": "frozen artifact"}')
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    construction = scripts / "build.py"
    construction.write_text("from helper import construct\n")
    (scripts / "helper.py").write_text("def construct():\n    return 1\n")
    (scripts / "lifecycle.py").write_text("def sweep():\n    return 1\n")
    lockfile = tmp_path / "uv.lock"
    lockfile.write_text("version = 1\n")
    return dict(
        repository=tmp_path,
        chain=chain,
        package=package,
        construction=construction,
        lockfile=lockfile,
        server={"cluster": "independent-cluster", "template_oid": 17},
    )


@pytest.mark.parametrize(
    "target",
    [
        "chain",
        "artifact",
        "module",
        "transitive",
        "initializer",
        "construction",
        "build_helper",
        "lockfile",
        "server",
    ],
)
def test_key_changes_for_declared_construction_inputs(source_tree, target):
    before, _ = deployment_key(**source_tree)
    path = {
        "chain": source_tree["chain"] / "revision.py",
        "artifact": source_tree["chain"] / "state.json",
        "module": source_tree["package"] / "selected.py",
        "transitive": source_tree["package"] / "transitive.py",
        "initializer": source_tree["package"] / "__init__.py",
        "construction": source_tree["construction"],
        "build_helper": source_tree["construction"].parent / "helper.py",
        "lockfile": source_tree["lockfile"],
    }.get(target)
    if path is not None:
        path.write_text(path.read_text() + "\n# changed construction input\n")
    else:
        source_tree["server"] = {"cluster": "reprovisioned-cluster", "template_oid": 17}
    after, _ = deployment_key(**source_tree)
    assert before != after


@pytest.mark.parametrize("target", ["unrelated.py", "lifecycle.py"])
def test_key_ignores_unrelated_package_and_sweep_changes(source_tree, target):
    before, components = deployment_key(**source_tree)
    path = (
        source_tree["package"] / target
        if target == "unrelated.py"
        else source_tree["construction"].parent / target
    )
    path.write_text(path.read_text() + "\n# unrelated change\n")
    after, later = deployment_key(**source_tree)
    assert after == before
    assert later == components


def test_revision_function_import_counts_but_package_lazy_import_does_not(source_tree):
    path = source_tree["chain"] / "revision.py"
    path.write_text(
        path.read_text() + "\ndef upgrade():\n    from corpus_structure import unrelated\n"
    )
    before, components = deployment_key(**source_tree)
    (source_tree["package"] / "unrelated.py").write_text("VALUE = 2\n")
    assert deployment_key(**source_tree)[0] != before
    assert any(name.endswith("unrelated.py") for name, _ in components["module_imports"])
    (source_tree["package"] / "unrelated.py").write_text("def lazy():\n    from . import unused\n")
    unused = source_tree["package"] / "unused.py"
    unused.write_text("VALUE = 1\n")
    before, _ = deployment_key(**source_tree)
    unused.write_text("VALUE = 2\n")
    assert deployment_key(**source_tree)[0] == before


def test_module_resolution_never_executes_selected_package_initializers(source_tree):
    (source_tree["package"] / "__init__.py").write_text("raise RuntimeError('must not import')\n")
    deployment_key(**source_tree)


def test_construction_does_not_follow_uncalled_lazy_package_apis(source_tree):
    (source_tree["package"] / "__init__.py").write_text(
        "def unused_api():\n    from . import unrelated\n"
    )
    source_tree["construction"].write_text("from corpus_structure import selected\n")
    before, components = deployment_key(**source_tree)
    (source_tree["package"] / "unrelated.py").write_text("VALUE = 7\n")
    assert deployment_key(**source_tree)[0] == before
    assert not any(name.endswith("unrelated.py") for name, _ in components["construction"])


def test_initializer_facade_import_does_not_select_uncalled_implementation(source_tree):
    (source_tree["package"] / "__init__.py").write_text("from .facade import unused_api\n")
    (source_tree["package"] / "facade.py").write_text(
        "def unused_api():\n    from . import unrelated\n"
    )
    source_tree["construction"].write_text("from corpus_structure import selected\n")
    before, components = deployment_key(**source_tree)
    (source_tree["package"] / "unrelated.py").write_text("VALUE = 7\n")
    assert deployment_key(**source_tree)[0] == before
    assert not any(name.endswith("unrelated.py") for name, _ in components["construction"])


def test_direct_constructor_helper_keeps_its_nested_local_dependency(source_tree):
    folder = source_tree["construction"].parent
    (folder / "helper.py").write_text("def construct():\n    from inner import value\n")
    (folder / "inner.py").write_text("value = 1\n")
    before, components = deployment_key(**source_tree)
    (folder / "inner.py").write_text("value = 2\n")
    assert deployment_key(**source_tree)[0] != before
    assert any(name.endswith("inner.py") for name, _ in components["construction"])


def test_real_chain_closure_contains_known_direct_machinery():
    from corpus_structure.semantic.migrations import ALEMBIC_DIR

    root = Path(__file__).resolve().parents[2]
    _, components = deployment_key(
        repository=root,
        chain=ALEMBIC_DIR,
        package=root / "python/corpus-structure/src/corpus_structure",
        construction=root / "scripts/native_deployment_build.py",
        lockfile=root / "uv.lock",
        server={"cluster": "source-inspection"},
    )
    selected = {Path(name).name for name, _ in components["module_imports"]}
    assert {
        "native_objects.py",
        "alembic_native.py",
        "alembic_defaults.py",
        "alembic_privileges.py",
    } <= selected
    assert {"metadata.py", "relational.py"}.isdisjoint(selected)
    assert not any("semantic_alembic/" in name for name, _ in components["chain"])
    construction = {Path(name).name for name, _ in components["construction"]}
    assert {"native_deployment_build.py", "extensions.py", "migrations.py"} <= construction
    assert "native_test_support.py" not in construction


def test_executed_body_imports_and_bytes_are_construction_inputs(source_tree):
    body = source_tree["chain"] / "upgrade.txt"
    body.write_text("from corpus_structure import unrelated\ndef upgrade():\n    pass\n")
    revision = source_tree["chain"] / "revision.py"
    revision.write_text("NATIVE_UPGRADE_FILE = 'upgrade.txt'\n")
    before, components = deployment_key(**source_tree)
    assert any(name.endswith("unrelated.py") for name, _ in components["module_imports"])
    (source_tree["package"] / "unrelated.py").write_text("VALUE = 3\n")
    assert deployment_key(**source_tree)[0] != before
    body.unlink()
    with pytest.raises(FileNotFoundError):
        deployment_key(**source_tree)


def test_executed_body_content_and_new_import_each_change_key(source_tree):
    body = source_tree["chain"] / "upgrade.txt"
    body.write_text("def upgrade():\n    return 1\n")
    (source_tree["chain"] / "revision.py").write_text("NATIVE_UPGRADE_FILE = 'upgrade.txt'\n")
    initial, _ = deployment_key(**source_tree)
    body.write_text("def upgrade():\n    return 2\n")
    changed, _ = deployment_key(**source_tree)
    assert changed != initial
    body.write_text(body.read_text() + "\nfrom corpus_structure import unrelated\n")
    imported, components = deployment_key(**source_tree)
    assert imported != changed
    assert any(name.endswith("unrelated.py") for name, _ in components["module_imports"])


@pytest.mark.parametrize(
    "fact,value",
    [
        ("server_version", "180001"),
        ("cluster", "other-cluster"),
        ("template_oid", 18),
        ("extensions", {"vector": "0.9.0"}),
    ],
)
def test_each_observed_server_fact_changes_key(source_tree, fact, value):
    source_tree["server"] = {
        "server_version": "180000",
        "cluster": "independent-cluster",
        "template_oid": 17,
        "extensions": {"vector": "0.8.2"},
        "principals": {"roles": [], "memberships": []},
    }
    before, _ = deployment_key(**source_tree)
    source_tree["server"][fact] = value
    assert deployment_key(**source_tree)[0] != before


def test_timestamp_changes_do_not_change_key(source_tree):
    before, components = deployment_key(**source_tree)
    for path in source_tree["repository"].rglob("*"):
        if path.is_file():
            os.utime(path, ns=(1000000000, 1000000000))
    assert deployment_key(**source_tree) == (before, components)


def test_equal_content_in_another_checkout_has_the_same_key(source_tree):
    before = deployment_key(**source_tree)
    original = source_tree["repository"]
    copied = original.with_name(original.name + "-copy")
    shutil.copytree(original, copied)
    relocated = {
        **source_tree,
        **{
            name: copied / source_tree[name].relative_to(original)
            for name in ("repository", "chain", "package", "construction", "lockfile")
        },
    }
    assert deployment_key(**relocated) == before


def test_unpinned_artifact_content_changes_key_with_size_and_timestamps_restored(source_tree):
    artifact = source_tree["chain"] / "state.json"
    original = artifact.read_bytes()
    observed = artifact.stat()
    before, _ = deployment_key(**source_tree)
    altered = original.replace(b"frozen", b"wrong!")
    assert altered != original and len(altered) == len(original)
    artifact.write_bytes(altered)
    os.utime(artifact, ns=(observed.st_atime_ns, observed.st_mtime_ns))
    assert artifact.stat().st_size == observed.st_size
    assert artifact.stat().st_mtime_ns == observed.st_mtime_ns
    assert deployment_key(**source_tree)[0] != before


def test_interpreter_version_is_a_key_determinant(source_tree, monkeypatch):
    import native_deployment_key

    before, _ = deployment_key(**source_tree)
    monkeypatch.setattr(
        native_deployment_key.sys, "version", native_deployment_key.sys.version + "+authored-change"
    )
    assert deployment_key(**source_tree)[0] != before


def test_key_components_match_independently_named_determinant_groups(source_tree):
    _, components = deployment_key(**source_tree)
    assert set(components) == {
        "chain",
        "artifacts",
        "module_imports",
        "construction",
        "lockfile",
        "interpreter",
        "server",
    }


def test_pinned_artifact_identity_uses_checked_declaration(source_tree):
    from corpus_structure.semantic.migrations import ALEMBIC_DIR

    artifact = source_tree["chain"] / "state.json"
    expected = sha256(artifact.read_bytes()).hexdigest()
    revision = source_tree["chain"] / "revision.py"
    revision.write_text(f"NATIVE_STATE_FILE = 'state.json'\nNATIVE_STATE_SHA256 = {expected!r}\n")
    before, components = deployment_key(**source_tree)
    assert components["artifacts"] == []
    artifact.write_text("altered bytes")
    assert deployment_key(**source_tree)[0] == before
    namespace = runpy.run_path(str(ALEMBIC_DIR / "versions" / "semantic_ddo_current_root.py"))
    load = namespace["_read"]
    load.__globals__["__file__"] = str(revision)
    with pytest.raises(RuntimeError, match="frozen native artifact differs"):
        load("state.json", expected)


@pytest.mark.parametrize(
    "attribute",
    [
        "rolcanlogin",
        "rolinherit",
        "rolsuper",
        "rolcreatedb",
        "rolcreaterole",
        "rolreplication",
        "rolbypassrls",
        "set_option",
        "inherit_option",
        "admin_option",
    ],
)
def test_observed_role_policy_changes_key_with_stable_identity(source_tree, attribute):
    source_tree["server"]["principals"] = {
        "roles": [
            {
                "rolname": "reader",
                "oid": 91,
                "rolcanlogin": False,
                "rolinherit": False,
                "rolsuper": False,
                "rolcreatedb": False,
                "rolcreaterole": False,
                "rolreplication": False,
                "rolbypassrls": False,
            }
        ],
        "memberships": [
            {
                "member": 91,
                "roleid": 92,
                "grantor": 93,
                "member_name": "reader",
                "role_name": "publisher",
                "grantor_name": "operator",
                "set_option": False,
                "inherit_option": False,
                "admin_option": False,
            }
        ],
    }
    before, _ = deployment_key(**source_tree)
    group = "roles" if attribute.startswith("rol") else "memberships"
    source_tree["server"]["principals"][group][0][attribute] = True
    assert deployment_key(**source_tree)[0] != before


@pytest.mark.parametrize("identity", ["member", "roleid", "grantor"])
def test_effective_membership_identity_changes_key(source_tree, identity):
    source_tree["server"]["principals"] = {
        "roles": [],
        "memberships": [
            {
                "member": 91,
                "roleid": 92,
                "grantor": 93,
                "member_name": "reader",
                "role_name": "publisher",
                "grantor_name": "operator",
                "set_option": True,
                "inherit_option": False,
                "admin_option": False,
            }
        ],
    }
    before, _ = deployment_key(**source_tree)
    source_tree["server"]["principals"]["memberships"][0][identity] += 10
    assert deployment_key(**source_tree)[0] != before


def test_retired_principal_shell_mode_refuses_before_host_access():
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ["bash", str(root / "scripts/pg_semantic_roles.sh"), "--principals"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2
    assert "usage: pg_semantic_roles.sh [--fitter-only]" in result.stderr


def test_server_owner_selects_production_migration_directory(source_tree, monkeypatch):
    import native_deployment_key
    from corpus_structure.core.db import host_bootstrap
    from corpus_structure.semantic import migrations
    from native_test_support import PgAdmin

    class Connection:
        def exec_driver_sql(self, statement):
            return SimpleNamespace(one=lambda: (180000, "cluster"))

        def execute(self, statement, parameters):
            return SimpleNamespace(scalar_one=lambda: 17)

    @contextmanager
    def connect(self):
        yield Connection()

    selected = []

    def compute(**inputs):
        selected.append(inputs)
        return "selected-chain-key", {}

    monkeypatch.setattr(migrations, "ALEMBIC_DIR", source_tree["chain"])
    monkeypatch.setattr(PgAdmin, "connect", connect)
    monkeypatch.setattr(PgAdmin, "installed", lambda self: {})
    monkeypatch.setattr(host_bootstrap, "observe_semantic_role_policy", lambda conn, names: {})
    monkeypatch.setattr(native_deployment_key, "deployment_key", compute)
    server = PgAdmin("postgresql+psycopg:///unused", "template0", expected={})
    assert server.deployment_key(source_tree["repository"]) == "selected-chain-key"
    assert selected[0]["chain"] == source_tree["chain"]
    assert server.deployment_key(source_tree["repository"]) == "selected-chain-key"
    assert len(selected) == 1
