"""Declared deployment-key boundaries on independent source trees."""

from pathlib import Path

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


def test_chain_function_body_import_stays_outside_module_level_closure(source_tree):
    path = source_tree["chain"] / "revision.py"
    path.write_text(
        path.read_text() + "\ndef upgrade():\n    from corpus_structure import unrelated\n"
    )
    before, components = deployment_key(**source_tree)
    (source_tree["package"] / "unrelated.py").write_text("VALUE = 2\n")
    assert deployment_key(**source_tree)[0] == before
    assert not any(name.endswith("unrelated.py") for name, _ in components["module_imports"])


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
    root = Path(__file__).resolve().parents[2]
    _, components = deployment_key(
        repository=root,
        chain=root / "python/corpus-structure/semantic_alembic",
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
        "alembic_indexes.py",
        "metadata.py",
        "migrations.py",
        "relational.py",
    } <= selected
    construction = {Path(name).name for name, _ in components["construction"]}
    assert {"native_deployment_build.py", "extensions.py", "migrations.py"} <= construction
    assert "native_test_support.py" not in construction
