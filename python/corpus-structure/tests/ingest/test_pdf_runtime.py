"""Initialized PDF custody checks distinguish code, object and model-file changes."""

from hashlib import sha256
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from corpus_structure.ingest.pdf_assets import PreparedPdfAssets
from corpus_structure.ingest.pdf_runtime import capture_initialized_pdf_runtime
from corpus_structure.semantic.file_custody import FileCustodyError


class Stage:
    def __call__(self, document):
        return document


class Pipeline:
    def __init__(self):
        self.assemble_model = Stage()
        self.enrichment_pipe = [Stage()]


class Options(BaseModel):
    threads: int = 1


def acquired(tmp_path):
    file = tmp_path / "model.bin"
    file.write_bytes(b"actual model")
    assets = PreparedPdfAssets(
        tmp_path,
        b"model manifest",
        ((file.name, sha256(file.read_bytes()).hexdigest()),),
    )
    owner = SimpleNamespace(_converter=Stage(), _pipeline=Pipeline(), _formula=None)
    return owner, capture_initialized_pdf_runtime(owner, assets=assets)


def test_initialized_pipeline_refuses_replaced_stage_and_population(tmp_path):
    owner, runtime = acquired(tmp_path)
    runtime.check()
    owner._pipeline.assemble_model = Stage()
    with pytest.raises(ValueError, match=r"binding changed: pipeline\.assemble_model"):
        runtime.check()
    owner, runtime = acquired(tmp_path)
    owner._pipeline.enrichment_pipe.append(Stage())
    with pytest.raises(ValueError, match=r"pipeline\.enrichment_pipe\.length"):
        runtime.check()


def test_initialized_pipeline_refuses_rebound_algorithm(tmp_path, monkeypatch):
    owner, runtime = acquired(tmp_path)
    original = Stage.__call__

    def replacement(self, document):
        return None

    monkeypatch.setattr(original, "__code__", replacement.__code__)
    with pytest.raises(ValueError, match="runtime code changed"):
        runtime.check()
    assert capture_initialized_pdf_runtime(owner, assets=runtime.assets).digest != runtime.digest


def test_initialized_pipeline_rechecks_model_file_without_version_change(tmp_path):
    _, runtime = acquired(tmp_path)
    (tmp_path / "model.bin").write_bytes(b"other model")
    with pytest.raises(FileCustodyError, match="acquired file changed"):
        runtime.check()


def test_initialized_pdf_format_refuses_backend_and_option_changes():
    option = SimpleNamespace(
        pipeline=Pipeline(),
        backend=Stage,
        pipeline_cls=Pipeline,
        pipeline_options=Options(),
        backend_options=Options(),
    )
    owner = SimpleNamespace(
        _converter=option,
        _pipeline=Pipeline(),
        _formula=None,
    )
    runtime = capture_initialized_pdf_runtime(owner, assets=None)
    option.backend = Pipeline
    with pytest.raises(ValueError, match=r"binding changed: converter\.pdf_backend"):
        runtime.check()
    option.backend = Stage
    option.backend_options.threads = 2
    with pytest.raises(ValueError, match="runtime options changed"):
        runtime.check()


def test_loaded_code_observation_is_relocatable_and_distinguishes_generated_code(tmp_path):
    def initialized(filename, result):
        namespace = {"__name__": __name__}
        exec(compile(f"def convert(self): return {result}", str(filename), "exec"), namespace)
        cls = type("Backend", (), {"__module__": __name__, "convert": namespace["convert"]})
        owner = SimpleNamespace(_converter=cls(), _pipeline=None, _formula=None)
        return capture_initialized_pdf_runtime(owner, assets=None)

    first = initialized(tmp_path / "first.py", 1)
    relocated = initialized(tmp_path / "second.py", 1)
    changed = initialized(tmp_path / "first.py", 2)
    assert first.digest == relocated.digest
    assert first.digest != changed.digest
