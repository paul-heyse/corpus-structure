"""Public ty requests against exact sources, with independent location expectations."""

import pytest

from corpus_structure.semantic.source_navigation import (
    NavigationRequest,
    NavigationSnapshot,
    SourceDocument,
    inspect_source_navigation,
    lsp_position,
)


def test_utf8_utf16_coordinate_fidelity():
    text = 'first\r\n"é😀"; result\n'
    offset = len('first\r\n"é😀"; '.encode())
    assert lsp_position(text, offset) == {"line": 1, "character": 7}
    with pytest.raises(UnicodeDecodeError):
        lsp_position("é", 1)


@pytest.mark.parametrize("path", ["../escape.py", "/absolute.py", "a/./b.py", "ty.toml"])
def test_source_snapshot_refuses_unsafe_or_ambiguous_paths(path):
    with pytest.raises(ValueError):
        SourceDocument(path=path, content="")


@pytest.mark.parametrize(
    "operation", ["definition", "declaration", "implementation", "references", "signature"]
)
def test_actual_ty_navigation_does_not_import_target(operation):
    source = 'raise RuntimeError("must never execute")\ndef twice(x: int) -> int:\n    return x * 2\n\nresult = twice(3)\n'
    snapshot = NavigationSnapshot(documents=(SourceDocument(path="example.py", content=source),))
    request = NavigationRequest(
        snapshot_id=snapshot.identity,
        path="example.py",
        byte_offset=source.encode().index(b"twice(3)") + (6 if operation == "signature" else 0),
        operation=operation,
    )
    result = inspect_source_navigation(snapshot, request)
    assert result.standing == "complete", result
    assert result.tool == "ty 0.0.102"
    if operation == "definition":
        assert result.items[0]["path"] == "example.py"
        assert result.items[0]["utf8_bytes"] == {
            "start": source.encode().index(b"twice(x"),
            "end": source.encode().index(b"twice(x") + 5,
        }
    if operation == "references":
        assert len(result.items) == 2


def test_wrong_snapshot_refused_before_starting_tool():
    snapshot = NavigationSnapshot(documents=())
    request = NavigationRequest(
        snapshot_id="wrong", path="example.py", byte_offset=0, operation="definition"
    )
    with pytest.raises(ValueError, match="another captured snapshot"):
        inspect_source_navigation(snapshot, request)


@pytest.mark.parametrize(
    "operation,direction,needle,expected",
    [
        ("call_hierarchy", "outgoing", "caller", "called"),
        ("call_hierarchy", "incoming", "called", "caller"),
        ("type_hierarchy", "supertypes", "Child", "Base"),
        ("type_hierarchy", "subtypes", "Base", "Child"),
    ],
)
def test_actual_hierarchy_locations(operation, direction, needle, expected):
    source = "class Base:\n    pass\nclass Child(Base):\n    pass\ndef called():\n    return 1\ndef caller():\n    return called()\n"
    snapshot = NavigationSnapshot(documents=(SourceDocument(path="example.py", content=source),))
    request = NavigationRequest(
        snapshot_id=snapshot.identity,
        path="example.py",
        byte_offset=source.encode().index(needle.encode()),
        operation=operation,
        direction=direction,
    )
    result = inspect_source_navigation(snapshot, request)
    assert result.standing == "complete", result
    import json

    assert expected in json.dumps(result.items)
    assert all("file://" not in json.dumps(row) for row in result.items)


def test_archived_bare_package_initializer_maps_to_package(monkeypatch):
    from hashlib import sha256
    from types import SimpleNamespace

    from corpus_structure.semantic import releases, source_interfaces
    from corpus_structure.semantic.source_navigation import archived_navigation_snapshot

    content = b"def member():\n    return 1\n"
    digest = sha256(content).hexdigest()
    facts = SimpleNamespace(
        modules=(
            SimpleNamespace(
                module="package",
                path="__init__.py",
                source_digest=digest,
                stub_digest=None,
                captured_artifact="data-operations/python/0.py",
            ),
        )
    )
    monkeypatch.setattr(releases, "open_release", lambda connection, release: object())
    monkeypatch.setattr(source_interfaces, "read_source_interfaces", lambda prepared: facts)

    class Connection:
        def execute(self, statement):
            return self

        def one(self):
            return SimpleNamespace(content=content, content_digest=digest)

    snapshot = archived_navigation_snapshot(Connection(), "release:captured")
    assert snapshot.documents[0].path == "package/__init__.py"
    assert snapshot.documents[0].content == content.decode()
