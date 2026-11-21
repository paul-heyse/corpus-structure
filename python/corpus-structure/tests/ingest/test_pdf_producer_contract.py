"""Selected producer custody, including preloaded calls and parent handoff."""

import collections
import importlib
import json
import sys
import sysconfig
from pathlib import Path
from types import SimpleNamespace

import pytest

from corpus_structure.ingest import pdf_producer_contract as producer
from corpus_structure.semantic.file_custody import observed_file
from corpus_structure.semantic.identity import canonical_bytes


def _small_contract():
    root = Path(producer.__file__).parents[1]
    names = (
        "__init__",
        "_query_custody",
        "semantic/file_custody",
        "semantic/identity",
        "ingest/pdf_producer_contract",
        "ingest/pdf_stream_types",
        "ingest/pdf",
    )
    files = tuple(
        (str(root / (name + ".py")), observed_file(root / (name + ".py")).digest) for name in names
    )
    stdlib = Path(sysconfig.get_path("stdlib")).resolve()
    runtime = tuple(
        (str(path), observed_file(path).digest)
        for path in stdlib.rglob("*.py")
        if "site-packages" not in path.parts
    )
    return producer.StandardPdfContract(b"{}", runtime, files)


def test_closed_population_accepts_source_and_refuses_preloaded_unselected_call():
    # Already imported modules cannot bypass the boundary by avoiding a new import.
    from corpus_structure.ingest.pdf_build_spool import canonical_native_options

    contract = _small_contract()
    from corpus_structure.ingest.pdf import PdfRecipe
    from corpus_structure.ingest.pdf_stream_types import PdfReplayRef

    pair = importlib.import_module("importlib.metadata._collections").Pair
    with producer.standard_pdf_execution(contract):
        assert canonical_bytes({"selected": True}) == b'{"selected":true}'
        assert PdfReplayRef(Path("unopened"), "a" * 64, 0, "test").family == "test"
        assert importlib.import_module("json") is json
        SelectedControl = collections.namedtuple("SelectedControl", "value")
        assert SelectedControl(3).value == 3
        assert pair("name", "value").name == "name"
        assert PdfRecipe("a" * 40, "b" * 40, device="cpu").device == "cpu"
    with (
        pytest.raises(ValueError, match="undeclared first-party helper"),
        producer.standard_pdf_execution(contract),
    ):
        canonical_native_options({})


def test_closed_population_refuses_replaced_loaded_code(monkeypatch):
    contract = _small_contract()
    original = canonical_bytes.__code__
    replacement = compile(
        "def canonical_bytes(value):\n return b'forged'", original.co_filename, "exec"
    )
    forged = next(value for value in replacement.co_consts if hasattr(value, "co_code"))
    monkeypatch.setattr(canonical_bytes, "__code__", forged)
    with (
        pytest.raises(ValueError, match="loaded code differs"),
        producer.standard_pdf_execution(contract),
    ):
        canonical_bytes({})


def test_selected_material_ignores_unrelated_files_and_authenticates_dependency(
    tmp_path, monkeypatch
):
    dependency = tmp_path / "dependency.py"
    dependency.write_text("x = 1\n")
    unrelated = tmp_path / "orchestration.py"
    unrelated.write_text("first\n")
    monkeypatch.setattr(producer, "STANDARD_MODULES", ("ingest/pdf_producer_contract",))
    monkeypatch.setattr(sys, "prefix", str(tmp_path))
    requirements = {
        "transformers": (
            "sentencepiece; extra == 'sentencepiece'",
            "protobuf; extra == 'sentencepiece'",
            "unused; extra == 'unused'",
        ),
        "sentencepiece": ("bridge[feature]",),
        "bridge": ("leaf; extra == 'feature'",),
        "jsonschema": ("format-leaf; extra == 'format'",),
    }
    monkeypatch.setattr(
        producer,
        "distribution",
        lambda name: SimpleNamespace(
            version="1.0",
            files=("dependency.py",),
            requires=requirements.get(name, ()),
            locate_file=lambda name: tmp_path / name,
        ),
    )
    producer.standard_pdf_contract.cache_clear()
    try:
        first = producer.standard_pdf_contract()
        unrelated.write_text("downstream changed\n")
        producer.standard_pdf_contract.cache_clear()
        second = producer.standard_pdf_contract()
        assert first.content == second.content
        document = json.loads(first.content)
        assert {"sentencepiece", "protobuf", "bridge", "leaf", "format-leaf"} <= set(
            document["distributions"]
        )
        assert "unused" not in document["distributions"]
        assert document["dependencies"] == [["dependency.py", observed_file(dependency).digest]]
        dependency.write_text("x = 2\n")
        with pytest.raises(ValueError, match="changed"):
            first.check()
    finally:
        producer.standard_pdf_contract.cache_clear()


def test_handoff_rejects_invented_or_missing_file_population():
    contract = _small_contract()
    root = Path(producer.__file__).parents[1]
    content = json.dumps(
        {
            "profile": producer.PROFILE,
            "first_party": [
                (str(Path(path).relative_to(root)), digest) for path, digest in contract.first_party
            ],
            "dependencies": [],
        }
    ).encode()
    producer.accept_standard_pdf_custody(
        content, tuple(item for item in contract.custody() if item[0] in dict(contract.first_party))
    )
    with pytest.raises(ValueError, match="selected population"):
        producer.accept_standard_pdf_custody(
            content,
            tuple(item for item in contract.custody() if item[0] in dict(contract.first_party))[
                :-1
            ],
        )
    changed = list(item for item in contract.custody() if item[0] in dict(contract.first_party))
    changed[0] = (changed[0][0], "0" * 64, *changed[0][2:])
    with pytest.raises(ValueError, match="admitted manifest"):
        producer.accept_standard_pdf_custody(content, tuple(changed))


def test_generic_sources_do_not_acquire_selected_recognition_population(monkeypatch):
    from corpus_structure.semantic.pdf_capture import standard_producer_from_sources

    def forbidden():
        pytest.fail("generic PDF sources acquired the selected recognition population")

    monkeypatch.setattr(producer, "standard_pdf_contract", forbidden)
    assert standard_producer_from_sources(SimpleNamespace(boundary_contracts=())) is None
    assert (
        standard_producer_from_sources(
            SimpleNamespace(
                boundary_contracts=(
                    SimpleNamespace(
                        name="pdf-capture/profile-assets",
                        content=b'{"version":"native-pdf-capture-v1"}',
                    ),
                )
            )
        )
        is None
    )
