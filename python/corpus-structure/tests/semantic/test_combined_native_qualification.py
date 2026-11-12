"""Opt-in actual six-provider residency and concurrent source-preserving requests.

Physical-peer fault controls in test_native_host cover destructive cancellation and
crash paths without repeatedly loading real models. This control establishes the
actual shared population; linguistic quality is assessed independently on the book.
"""

import base64
import json
import os
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from threading import Barrier, Lock

import pytest
import yaml

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.ingest.hosted_spacy import HostedPipeline
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.gliner import GlinerInput, GlinerPack
from corpus_structure.methods.m1_source import M1Config
from corpus_structure.methods.native_host import NativeHostGroup
from corpus_structure.methods.native_host_clients import gliner_host_payload
from corpus_structure.methods.native_profiles import (
    gliner_selection,
    pm2_selection,
    preflight_native_runtime,
)
from corpus_structure.methods.pm2_worker import _live_group
from corpus_structure.settings import Settings


@pytest.mark.gpu
@pytest.mark.skipif(
    not os.environ.get("CORPUS_PM2_NATIVE_TEST_ASSETS"), reason="locked native assets are opt-in"
)
def test_actual_six_provider_host_preserves_population_streams_and_sources(request):
    assets = Path(os.environ["CORPUS_PM2_NATIVE_TEST_ASSETS"])
    selections = {}
    for provider in ("d1", "hanlp", "maverick", "dipo"):
        checked = preflight_native_runtime(provider, assets)
        selections[provider] = pm2_selection(
            provider, assets, checked["runtime_identity"], checked["assets"]
        )
    root = Path(__file__).resolve().parents[4]
    config = yaml.safe_load((root / "domains/statistics/m1-methods.yaml").read_text())["configs"][
        "extract.m1_candidates"
    ]["default"]
    gliner = M1Config.model_validate(config).profile()
    selections["gliner"] = gliner_selection(
        gliner, preflight_native_runtime("gliner", gliner.snapshot)["runtime_identity"]
    )
    spacy = HostedPipeline(SentenceConfig(exclude=("ner",)))
    selections["spacy"] = spacy.selection()
    source = "Alice studied statistics. She liked it."
    sentences = [["Alice", "studied", "statistics", "."], ["She", "liked", "it", "."]]
    prepared = spacy._base.make_doc(source)
    expected_tokens = [(token.text, token.idx) for token in prepared]
    digest = sha256(source.encode()).hexdigest()
    pack = GlinerPack.from_declaration(
        "combined-native-qualification",
        {"entities": {"person": "named person"}},
        version="native-local-v1",
    )
    payloads = {
        "d1": {
            "state": {"source": "12"},
            "questions": {
                "value": {"type": "text", "instructions": "Copy the numeral as written."}
            },
        },
        "hanlp": {"sentences": sentences},
        "maverick": {"sentences": sentences},
        "dipo": {"text": source, "mode": "learned"},
        "spacy": {
            "version": "spacy-host-1",
            "documents": [{"content": base64.b64encode(prepared.to_bytes()).decode("ascii")}],
        },
        "gliner": gliner_host_payload(
            pack, (GlinerInput("combined-source", digest, source),), 0.5, "flat"
        ),
    }
    observation_lock = Lock()
    in_flight = set()
    barrier = Barrier(len(selections))
    with NativeHostGroup(CharacterizationExecutionPolicy(), Settings().nemotron.endpoint) as group:
        group.declare(tuple(selections.values()))
        group.ensure(lambda: None)
        assert set(group._hosts) == {"primary"}
        host = group._hosts["primary"]
        assert host._process is not None
        pid = host._process.pid
        startup = {key: group.startup(value, lambda: None) for key, value in selections.items()}
        assert set(host.startup) == {value.native.fingerprint for value in selections.values()}
        streams = {value["host_stream"] for value in startup.values()}
        assert len(streams) == 6 and 0 not in streams
        for provider, value in startup.items():
            assert value["device"].split(":")[0] == "cuda"
            assert value["dtype"] == ("torch.bfloat16" if provider == "d1" else "torch.float32")
            assert value["profile"] == selections[provider].native.fingerprint
        assert startup["spacy"]["gpu_parameter_arrays"] > 0
        assert all(
            row["reason"] == "spacy-transition-native-cpu-upper"
            for row in startup["spacy"]["native_cpu_upper_parameters"]
        )

        def active():
            with host._lock:
                population = frozenset(item.selection.provider for item in host._pending.values())
            with observation_lock:
                in_flight.add(population)

        def infer(provider):
            barrier.wait(timeout=10)
            return provider, group.infer(selections[provider], payloads[provider], active)

        with ThreadPoolExecutor(max_workers=6) as pool:
            results = dict(pool.map(infer, selections))
        assert max(map(len, in_flight)) >= 2
        assert not host._pending
        assert results["d1"]["outcome"] == "succeeded"
        assert tuple(results["d1"]["native"]["answers"]) == ("value",)
        assert results["d1"]["native"]["answers"]["value"]["text"] == "12"
        assert results["hanlp"]["outcome"] == "succeeded"
        assert results["hanlp"]["native"]["tok"] == sentences
        assert results["maverick"]["tokens"] == [
            token for sentence in sentences for token in sentence
        ]
        assert results["dipo"]["outcome"] == "succeeded"
        for edu in results["dipo"]["edus"]:
            start, end = edu["chars"]
            assert " ".join(source[start:end].split()) == edu["text"]
        (annotated,) = spacy.decode(results["spacy"]["documents"])
        assert annotated.text == source
        assert [(token.text, token.idx) for token in annotated] == expected_tokens
        (report,) = results["gliner"]["reports"]
        assert report["context_id"] == "combined-source" and report["context_digest"] == digest
        assert report["profile"] == gliner.fingerprint
        assert report["member_ordinal"] == 0
        results["spacy"] = {
            "source": annotated.text,
            "tokens": [
                {
                    "text": token.text,
                    "start": token.idx,
                    "end": token.idx + len(token),
                    "lemma": token.lemma_,
                    "pos": token.pos_,
                    "dependency": token.dep_,
                    "head": token.head.i,
                }
                for token in annotated
            ],
        }
        startup_fields = (
            "provider",
            "profile",
            "device",
            "dtype",
            "backend",
            "host_stream",
            "native_threads",
        )
        observed = dict(
            source=source,
            sentences=sentences,
            pid=pid,
            startup={
                provider: {key: value[key] for key in startup_fields}
                for provider, value in startup.items()
            },
            simultaneous_pending_providers=[
                sorted(value) for value in sorted(in_flight, key=lambda v: tuple(sorted(v)))
            ],
            results=results,
        )
    assert group._closed and host._process.poll() is not None and not _live_group(pid)
    observed["cleanup"] = "owned group absent after production close"
    request.node.user_properties.append(("actual_six_provider_qualification", json.dumps(observed)))
