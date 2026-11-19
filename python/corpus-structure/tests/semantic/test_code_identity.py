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
    first = capture_code_identity(root, ("example.entry",))
    assert first.complete
    assert {x.module for x in first.modules} == {"example", "example.entry", "example.value"}
    (root / "value.py").write_text("# harmless layout\ndef answer():\n    return 7\n")
    assert capture_code_identity(root, ("example.entry",)).digest == first.digest
    (root / "value.py").write_text("def answer():\n return 8\n")
    assert capture_code_identity(root, ("example.entry",)).digest != first.digest


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
    assert capture_code_identity(root, ("example.entry",)).complete


def test_package_location_does_not_determine_code_identity(tmp_path):
    first = package(tmp_path)
    (first / "entry.py").write_text("def answer():\n return 7\n")
    second = tmp_path / "copy" / "example"
    second.mkdir(parents=True)
    for source in first.glob("*.py"):
        (second / source.name).write_bytes(source.read_bytes())
    assert (
        capture_code_identity(first, ("example.entry",)).digest
        == capture_code_identity(second, ("example.entry",)).digest
    )


def test_incomplete_serving_computes_a_fresh_page_without_reuse_handles():
    from corpus_structure.semantic.code_identity import CodeIdentity, CodeUnknown
    from corpus_structure.semantic.selected_query_cache import (
        SelectedQueryCache,
        bounded_rows,
        byte_bounded_page,
    )
    from corpus_structure.semantic.serving_code import ServingImplementation, serving_code

    basis = CodeIdentity(
        ("example.entry",), (), (), (CodeUnknown("example.entry", 4, "dynamic"),), b"{}"
    )
    implementation = ServingImplementation("a" * 64, basis)
    cache = SelectedQueryCache()
    entry, _ = bounded_rows((7,), {})
    assert entry is not None
    with serving_code(implementation):
        assert cache.put(b"key", entry) is False
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
    assert cache.get(b"key") is None
