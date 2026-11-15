"""Independent captured/proposed discovery and coordinate expectations."""

from corpus_structure.schema.model_discovery import discover_source_consumers, locate_consumers


def test_snapshot_discovery_uses_exact_proposed_bytes_and_complete_membership(tmp_path):
    directory = tmp_path / "python/corpus-structure/src"
    directory.mkdir(parents=True)
    for index in range(405):
        (directory / f"module_{index:03}.py").write_text("x = 1\n")
    consumer = directory / "untracked.py"
    consumer.write_text("old()\n")
    relative = consumer.relative_to(tmp_path).as_posix()
    report = locate_consumers(tmp_path, "head", {"new"}, proposed={relative: "new()\n"})
    assert len(report["inspected"]) == 406
    assert report["unscanned_files"] == 0
    assert report["coverage"] == "complete-syntax-examination"
    assert [(row["path"], row["source"]) for row in report["candidates"]] == [(relative, "new")]
    assert consumer.read_text() == "old()\n"
    assert report["semantic_coverage"]["status"] == "unknown"


def test_native_queries_keep_alias_shadow_and_unicode_byte_evidence():
    source = "from api import target as alias\r\ndef f(target: int):\r\n    return 'é😀', target\r\nvalue = alias(1)\r\n"
    report = discover_source_consumers({"source.py": source.encode()}, {"target", "alias"})
    shadow = next(row for row in report["candidates"] if row["line"] == 3)
    start = source.encode().index(b"target", source.encode().index(b"return"))
    assert shadow["utf8_bytes"] == {"start": start, "end": start + 6}
    assert shadow["utf8_column"] == len("    return 'é😀', ".encode())
    assert shadow["qualified_names"] == [{"name": "f.<locals>.target", "origin": "LOCAL"}]
    called = next(row for row in report["candidates"] if row["line"] == 4)
    assert called["category"] == "call"
    assert called["qualified_names"] == [{"name": "api.target", "origin": "IMPORT"}]


def test_unsupported_encoding_is_visible_partial_scope():
    report = discover_source_consumers({"latin.py": b'# coding: latin-1\nx="\xe9"\n'}, {"x"})
    assert report["coverage"] == "partial-syntax-examination"
    assert report["skipped"] == {"latin.py": "ValueError"}
    assert report["unscanned_files"] == 1
