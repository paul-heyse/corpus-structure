"""Independent examples for source discovery and reusable code standing."""

from corpus_structure.semantic.code_identity import capture_code_identity


def package(tmp_path):
    root = tmp_path / "example"
    root.mkdir()
    (root / "__init__.py").write_text("")
    return root


def test_function_local_relative_import_is_discovered_without_target_import(tmp_path):
    root = package(tmp_path)
    (root / "entry.py").write_text("def result():\n from .value import answer\n return answer()\n")
    (root / "value.py").write_text("def answer():\n return 7\n")
    first = capture_code_identity(root, ("example.entry",), callables=("example.entry.result",))
    assert first.complete
    assert {x.module for x in first.modules} == {"example", "example.entry", "example.value"}
    (root / "value.py").write_text("# harmless layout\ndef answer():\n    return 7\n")
    assert (
        capture_code_identity(root, ("example.entry",), callables=("example.entry.result",)).digest
        == first.digest
    )
    (root / "value.py").write_text("def answer():\n return 8\n")
    assert (
        capture_code_identity(root, ("example.entry",), callables=("example.entry.result",)).digest
        != first.digest
    )


def test_dynamic_import_reports_incomplete_without_import_or_exception(tmp_path):
    root = package(tmp_path)
    (root / "entry.py").write_text(
        "import importlib\ndef result(name):\n return importlib.import_module(name)\n"
    )
    value = capture_code_identity(root, ("example.entry",))
    assert not value.complete and value.digest is None and value.observed_digest
    assert [(x.module, x.line, x.reason) for x in value.unknowns] == [
        ("example.entry", 3, "nonliteral dynamic import")
    ]


def test_type_checking_import_is_not_required_at_execution(tmp_path):
    root = package(tmp_path)
    (root / "entry.py").write_text(
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n import absent_dependency\ndef result():\n return 3\n"
    )
    observed = capture_code_identity(root, ("example.entry",))
    assert not observed.complete
    assert all("absent_dependency" not in item.reason for item in observed.unknowns)


def test_package_location_does_not_determine_code_identity(tmp_path):
    first = package(tmp_path)
    (first / "entry.py").write_text("def answer():\n return 7\n")
    second = tmp_path / "copy" / "example"
    second.mkdir(parents=True)
    for source in first.glob("*.py"):
        (second / source.name).write_bytes(source.read_bytes())
    assert (
        capture_code_identity(first, ("example.entry",), callables=("example.entry.answer",)).digest
        == capture_code_identity(
            second, ("example.entry",), callables=("example.entry.answer",)
        ).digest
    )


def test_incomplete_serving_computes_a_fresh_page_without_reuse_handles():
    from corpus_structure.semantic.code_identity import CodeIdentity, CodeUnknown
    from corpus_structure.semantic.selected_query_cache import (
        SelectedQueryCache,
        ServedKey,
        bounded_rows,
        byte_bounded_page,
    )
    from corpus_structure.semantic.serving_code import ServingImplementation, serving_code

    basis = CodeIdentity(
        ("example.entry",), (), (), (CodeUnknown("example.entry", 4, "dynamic"),), b"{}"
    )
    implementation = ServingImplementation("a" * 64, basis)
    cache = SelectedQueryCache()
    key = ServedKey("test", b"selection", "implementation", ("reader",), "cut", b"current")
    entry, _ = bounded_rows((7,), {})
    assert entry is not None
    with serving_code(implementation):
        assert cache.put(key, entry) is False
        result = byte_bounded_page(
            iter([7, 8]),
            offset=0,
            limit=1,
            max_bytes=16384,
            report=lambda end, values, more: {
                "items": values,
                "cursor": "held",
                "resource_handle": "held",
                "page_complete": not more,
            },
        )
    assert result["items"] == [7]
    assert result["cursor"] is None and result["resource_handle"] is None
    assert result["page_complete"] is False
    assert result["reuse"]["eligible"] is False
    assert cache.get(key) is None


def test_absent_serving_context_cannot_grant_cache_eligibility():
    from corpus_structure.semantic.selected_query_cache import (
        SelectedQueryCache,
        ServedKey,
        bounded_rows,
    )
    from corpus_structure.semantic.serving_code import reusable_serving_code

    assert not reusable_serving_code()
    cache = SelectedQueryCache()
    key = ServedKey("test", b"selection", "implementation", ("reader",), "cut", b"current")
    entry, _ = bounded_rows((7,), {})
    assert entry is not None
    assert not cache.put(key, entry)
    with cache.loading(key) as retained:
        assert retained is None


def test_serving_context_cannot_authorize_another_implementation():
    from corpus_structure.semantic.code_identity import CodeIdentity
    from corpus_structure.semantic.selected_query_cache import (
        SelectedQueryCache,
        ServedKey,
        bounded_rows,
    )
    from corpus_structure.semantic.serving_code import ServingImplementation, serving_code

    complete = CodeIdentity(("control",), (), (), (), b"{}")
    key = ServedKey("test", b"selection", "another", ("reader",), "cut", b"current")
    entry, _ = bounded_rows((7,), {})
    assert entry is not None
    with serving_code(ServingImplementation("current", complete)):
        assert not SelectedQueryCache().put(key, entry)


def test_discovery_alone_cannot_authorize_an_indirect_load(tmp_path):
    root = package(tmp_path)
    (root / "entry.py").write_text(
        "import importlib\ndef result():\n"
        " return getattr(importlib, 'import_module')('example.value').answer()\n"
    )
    (root / "value.py").write_text("def answer():\n return 7\n")
    discovered = capture_code_identity(root, ("example.entry",))
    assert discovered.digest is None
    closed = capture_code_identity(root, ("example.entry",), callables=("example.entry.result",))
    assert closed.digest is None
    assert any(item.line == 3 and "dynamic call target" in item.reason for item in closed.unknowns)


def test_only_the_selected_callable_initializes_its_local_imports(tmp_path):
    root = package(tmp_path)
    (root / "entry.py").write_text(
        "def result():\n return 1\n"
        "def unrelated():\n import unknown_provider\n return unknown_provider.run()\n"
    )
    basis = capture_code_identity(root, ("example.entry",), callables=("example.entry.result",))
    assert basis.complete
    other = capture_code_identity(root, ("example.entry",), callables=("example.entry.unrelated",))
    assert other.digest is None


def test_eager_effect_withholds_reuse_even_if_its_binding_is_unused(tmp_path):
    root = package(tmp_path)
    (root / "entry.py").write_text(
        "def setup():\n return 1\nvalue = setup()\ndef result():\n return 3\n"
    )
    basis = capture_code_identity(root, ("example.entry",), callables=("example.entry.result",))
    assert basis.digest is None
    assert any(item.line == 3 and "initializer" in item.reason for item in basis.unknowns)
