"""Passive preparation inputs and refusals need no runtime validation machinery."""

import subprocess
import sys


def test_passive_types_import_without_validation_or_runtime_configuration():
    reply = subprocess.run(
        [
            sys.executable,
            "-c",
            r"""
import sys
from corpus_structure.semantic.refusal_types import ReadLimit, SemanticRefusal, WrongRelease
from corpus_structure.semantic.types import SourceArtifact

assert SourceArtifact('input', b'abc').digest == 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
error = ReadLimit('bounded page', reason='response_bytes')
assert isinstance(error, SemanticRefusal)
assert str(error) == 'bounded page' and error.reason == 'response_bytes'
assert WrongRelease('other release').reason == 'wrong_release'
assert not {'pydantic', 'corpus_structure.settings', 'corpus_structure.caches', 'corpus_structure.semantic.refusals'} & sys.modules.keys()

from corpus_structure.model.compiled import CompiledModel

model = CompiledModel((('model.yaml', b'id: urn:passive\nname: passive\n'),))
assert model.sources['model.yaml'].startswith(b'id: urn:passive')
assert not {'corpus_structure.settings', 'corpus_structure.caches'} & sys.modules.keys()
""",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert reply.returncode == 0, reply.stdout + reply.stderr
