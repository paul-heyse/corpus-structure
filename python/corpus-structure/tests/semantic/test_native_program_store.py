"""Independent exact program artifact round trips and refusal of changed identities."""

import os
from dataclasses import replace

import pytest
from sqlalchemy import MetaData

from corpus_structure.semantic.native_objects import NativeDefinition, NativeIdentity
from corpus_structure.semantic.native_products import NativeAuthoringInputs
from corpus_structure.semantic.native_program_registry import ProgramManifest
from corpus_structure.semantic.native_program_store import ProgramSetArtifact
from corpus_structure.semantic.target_installation import FoundationPrograms, TargetInstallation
from corpus_structure.semantic.types import SourceArtifact


@pytest.fixture
def program_capture():
    program = NativeDefinition(
        NativeIdentity("function", "sem", "answer"),
        "CREATE OR REPLACE FUNCTION sem.answer() RETURNS integer LANGUAGE sql AS 'SELECT 7'",
        "independent program fixture",
        "corpus_sem_publisher",
        callees=frozenset(),
    )
    manifest = ProgramManifest.from_definitions((program,))
    sources = (
        SourceArtifact("native/program-manifest.json", manifest.content),
        SourceArtifact("authoring/identity.sql", b"identity\r\n"),
        SourceArtifact("authoring/closure.sql", b"closure\n"),
        SourceArtifact("authoring/closure-native.sql", b"native\n"),
        SourceArtifact("opaque", b"\x00\xff\x00", authoring_provenance=True),
    )
    metadata = MetaData(info={"physical_model_id": "physical:one"})
    return TargetInstallation(
        metadata=metadata,
        pdf_sources=(),
        authoring_inputs=NativeAuthoringInputs(sources, "physical:one", sources[:1], ()),
        foundation=FoundationPrograms("identity\r\n", "closure\n", "native\n", ()),
        pdf_descriptor=(),
        pdf_identity=(),
        programs=(program,),
    )


def test_serialized_programs_keep_exact_bytes_and_rebuild_metadata(program_capture):
    artifact = ProgramSetArtifact.capture(program_capture)
    decoded = ProgramSetArtifact.model_validate_json(artifact.model_dump_json())
    fresh_metadata = MetaData(info={"physical_model_id": "physical:one"})
    opened = decoded.hydrate(fresh_metadata)
    assert opened.metadata is fresh_metadata
    assert opened.programs == program_capture.programs
    assert opened.authoring_inputs.sources == program_capture.authoring_inputs.sources
    assert opened.foundation.native_closure == "native\n"
    assert opened.rendered_only


def test_altered_program_cannot_keep_another_programs_manifest(program_capture):
    artifact = ProgramSetArtifact.capture(program_capture)
    changed = replace(
        artifact.programs[0], sql=artifact.programs[0].sql.replace("SELECT 7", "SELECT 8")
    )
    with pytest.raises(ValueError, match="identities differ"):
        artifact.model_copy(update={"programs": (changed,)}).hydrate(program_capture.metadata)


def test_program_capture_cannot_bind_another_physical_model(program_capture):
    artifact = ProgramSetArtifact.capture(program_capture)
    with pytest.raises(ValueError, match="another physical model"):
        artifact.hydrate(MetaData(info={"physical_model_id": "physical:other"}))


def test_current_program_artifact_uses_captured_products_without_rendering(monkeypatch):
    from corpus_structure.semantic import target_installation
    from corpus_structure.semantic.metadata import get_metadata

    current = target_installation.capture_target_installation(get_metadata())
    artifact = ProgramSetArtifact.capture(current)
    opened = ProgramSetArtifact.model_validate_json(artifact.model_dump_json()).hydrate(
        current.metadata
    )

    def unexpected(*args, **kwargs):
        pytest.fail("a retained program set must not invoke native rendering")

    monkeypatch.setattr(target_installation, "target_native_declarations", unexpected)
    assert target_installation.target_program_definitions(None, opened) == current.programs
    assert target_installation.target_physical_prerequisites(None, opened) == current.prerequisites
    assert opened.authoring_inputs.sources == current.authoring_inputs.sources


def test_program_store_reopens_a_program_entry_without_building(tmp_path, monkeypatch):
    from corpus_structure import cache_store
    from corpus_structure.semantic import native_program_store, target_installation
    from corpus_structure.semantic.metadata import get_metadata

    store = cache_store.CacheStore(
        tmp_path / "cache", program_store_bytes=64 * 1024**2, page_store_bytes=0
    )
    monkeypatch.setattr(cache_store, "configured_store", lambda: store)
    current = target_installation.capture_target_installation(get_metadata())
    native_program_store.save_installation(b"program-set", current)

    def unexpected(*args, **kwargs):
        pytest.fail("the warm disk artifact must bypass the program builder")

    monkeypatch.setattr(target_installation, "_build_target_installation", unexpected)
    opened = native_program_store.load_installation(
        b"program-set",
        physical_sources=tuple(current.metadata.info["physical_sources"].items()),
        linkml_types=current.metadata.info["physical_linkml_types"],
    )
    assert opened is not None
    assert opened is not current
    assert opened.metadata.info["physical_model_id"] == current.metadata.info["physical_model_id"]
    assert opened.programs == current.programs
    assert opened.prerequisites == current.prerequisites
    assert opened.authoring_inputs.sources == current.authoring_inputs.sources
    assert opened.rendered_only


def test_program_store_miss_does_not_compile_physical_inputs(tmp_path, monkeypatch):
    from corpus_structure import cache_store
    from corpus_structure.schema import physical
    from corpus_structure.semantic import native_program_store

    store = cache_store.CacheStore(
        tmp_path / "cache", program_store_bytes=64 * 1024**2, page_store_bytes=0
    )
    monkeypatch.setattr(cache_store, "configured_store", lambda: store)

    def unexpected(*args, **kwargs):
        pytest.fail("a disk miss must leave physical compilation to the renderer")

    monkeypatch.setattr(physical, "compile_physical", unexpected)
    missing = native_program_store.load_installation(
        b"missing", physical_sources=(), linkml_types=b""
    )
    assert missing is None


@pytest.mark.skipif(
    os.environ.get("CORPUS_RUN_UDM_D2") != "1",
    reason="actual D2 qualification requires complete authenticated generator identity",
)
def test_installed_native_candidate_reuses_programs_in_a_fresh_offline_process(tmp_path):
    import json
    import subprocess
    import sys
    from pathlib import Path

    from corpus_structure.semantic.execution_admission import _revision_expectation
    from corpus_structure.semantic.migrations import ALEMBIC_DIR, head_revision
    from corpus_structure.semantic.native_authoring import load_native_state

    root = Path(__file__).resolve().parents[4]
    predecessor = head_revision()
    assert predecessor is not None
    frozen = _revision_expectation(ALEMBIC_DIR / "versions", predecessor)
    state_path, state_digest = frozen.state
    object_count = len(load_native_state(state_path, digest=state_digest))
    cache = tmp_path / "program-cache"
    unavailable = "postgresql+psycopg://paul@127.0.0.1:1/corpus_d2_offline?connect_timeout=1"
    environment = os.environ | {
        "CORPUS_CACHE__ROOT": str(cache),
        "CORPUS_CACHE__PROGRAM_STORE_BYTES": str(128 * 1024**2),
        "CORPUS_CACHE__PAGE_STORE_BYTES": "0",
        **{
            "CORPUS_DATABASE__" + purpose: unavailable
            for purpose in (
                "URL",
                "MAINTENANCE_URL",
                "READER_URL",
                "EVALUATOR_URL",
                "ADMISSION_URL",
            )
        },
    }
    script = """
import json
import os
import sys
from pathlib import Path

counts = {"render": 0, "hydrate": 0}
def observe(frame, event, arg):
    if event != "call":
        return
    module = frame.f_globals.get("__name__")
    if module == "corpus_structure.semantic.target_installation" and frame.f_code.co_name == "render_target_installation":
        counts["render"] += 1
    if module == "corpus_structure.semantic.native_program_store" and frame.f_code.co_name == "hydrate":
        counts["hydrate"] += 1

sys.setprofile(observe)
try:
    from corpus_structure.cli.app import main
    main()
finally:
    sys.setprofile(None)
    Path(os.environ["NATIVE_GENERATOR_COUNTS"]).write_text(json.dumps(counts))
"""
    command = [
        sys.executable,
        "-c",
        script,
        "schema",
        "native-candidate",
        "--expected-predecessor",
        predecessor,
        "--json",
    ]

    def invoke(ordinal):
        count_path = tmp_path / f"counts-{ordinal}.json"
        reply = subprocess.run(
            command,
            cwd=root,
            env=environment | {"NATIVE_GENERATOR_COUNTS": str(count_path)},
            capture_output=True,
            check=False,
            text=True,
            timeout=300,
        )
        assert reply.returncode == 0, reply.stdout + reply.stderr
        return json.loads(reply.stdout), json.loads(count_path.read_text())

    first, first_counts = invoke(1)
    entries = {path.relative_to(cache): path.read_bytes() for path in cache.rglob("programs.json")}
    second, second_counts = invoke(2)

    assert first["outcome"] == second["outcome"] == "no_native_change"
    assert first["head_revision"] == second["head_revision"] == predecessor
    assert first["object_count"] == second["object_count"] == object_count
    assert first["kernel_identity"] == second["kernel_identity"]
    observations = {
        "first": first_counts,
        "second": second_counts,
        "native_results": (first, second),
    }
    assert first_counts == {"render": 1, "hydrate": 0}, observations
    assert second_counts == {"render": 0, "hydrate": 1}, observations
    assert len(entries) == 1
    assert entries == {
        path.relative_to(cache): path.read_bytes() for path in cache.rglob("programs.json")
    }
