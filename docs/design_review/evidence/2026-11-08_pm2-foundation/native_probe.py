"""Exercise a locked PM2 worker over authenticated development source slices."""

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic

import httpx

from corpus_structure.core.method import UnitRef
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.methods.pm2_result import pm2_input_digest, pm2_unit_result
from corpus_structure.methods.pm2_source import (
    D1SourceField,
    PM2SourceMap,
    PM2TokenMap,
    ProviderToken,
    SourceMapSegment,
)
from corpus_structure.methods.pm2_worker import open_pm2_worker
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_contexts import NativeSourceContext, SourceSlice
from corpus_structure.settings import Settings

ROOT = Path(__file__).resolve().parents[4]
RUN, CUT, VIEW = 404, 514, 383
RELEASE = "release:675b5f723ce83aadf7b8b1df7f0784fdc2c455d02b3979f1eae2cec30c352a56"
PROJECTION = "87f5af8a57fea55961e93d25d46ac4283ed24069772bcf41d0919f37a5a1eaa2"
PROVIDER_SCRIPT = (
    ROOT / "python/corpus-structure/src/corpus_structure/methods/pm2_native.py"
)
SCOPES = ((811, 907), (811, 1018))


def inputs(view, scope):
    start, end = scope
    primary = native_source_frame(view, ())
    context = NativeSourceContext(
        primary, (), (SourceSlice(VIEW, start, end),),
        "PM2 native profile exercise", "pm2-foundation-1", "frozen source-only scope",
    )
    positions = (811, 908)
    effective = []
    atoms = []
    for token in view.layout.tokens:
        if token.end <= start or token.start >= end:
            continue
        if not start <= token.start < token.end <= end:
            raise ValueError("frozen control cuts a canonical token")
        text = view.text[token.start:token.end]
        if token.role != "prose":
            atoms.append((token.start - start, token.end - start))
        if text.strip():
            effective.append(ProviderToken(
                text, token.start - start, token.end - start, int(token.start >= positions[1])
            ))
    mapping = PM2SourceMap(
        context, context.text, (SourceMapSegment(0, len(context.text), 0),), tuple(atoms)
    )
    tokens = PM2TokenMap(mapping, tuple(effective))
    return mapping, tokens


def run_request(provider, worker, mapping, tokens):
    text = mapping.provider_text
    sentences = [
        [token.text for token in tokens.sentence_tokens(index)]
        for index in sorted({token.sentence for token in tokens.tokens})
    ]
    if provider == "d1":
        request = {
            "state": {"source": text},
            "questions": {
                "definition_term": {"type": "text", "instructions": "Copy the exact term being defined."},
                "definition_value": {
                    "type": "text", "instructions": "Copy the phrase that says what its value is."
                },
            },
        }
    elif provider == "dipo":
        request = {"text": text}
    else:
        request = {"sentences": sentences}
    reply = worker.infer(request)
    field = None
    if provider == "d1" and reply["outcome"] == "succeeded":
        (start, end, path), = (row for row in reply["state_fields"] if row[2] == "/source")
        field = D1SourceField(reply["rendered_state"], path, start, end)
    source_map = tokens if provider in {"hanlp", "maverick"} else mapping
    ref = UnitRef(TaskUnitType.SOURCE_VIEW, VIEW, mapping.context.primary.unit_ref)
    source_path = "/source" if provider == "d1" else None
    result = pm2_unit_result(
        ref, source_map, profile=worker.startup, request=request, reply=reply, field=field,
        question="provider_grounding_probe", operation_version="1", source_path=source_path,
        input_digest=pm2_input_digest(
            source_map, worker.startup, request, question="provider_grounding_probe",
            operation_version="1", source_path=source_path,
        ),
    )
    return result.parse_detail["pm2_native"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("provider", choices=("d1", "dipo", "hanlp", "maverick"))
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    parser.add_argument("--assets", type=Path, default=ROOT / "build/models/pm2")
    parser.add_argument("--cancel-d1", action="store_true")
    args = parser.parse_args()
    provider = args.provider
    if args.cancel_d1 and (provider != "d1" or args.device != "cuda"):
        parser.error("--cancel-d1 requires the CUDA d1 profile")
    python = Path(sys.executable) if provider == "d1" else (
        ROOT / f"services/pm2-{provider}/.venv/bin/python"
    )
    settings = Settings()
    with open_runtime_engine(settings, "pm2-foundation-probe", purpose="read") as engine:
        with engine.connect() as conn:
            prepared = open_release(conn, RELEASE)
            view = BoundReader(conn, RUN, prepared, CUT).source_view(VIEW)
    if view.ref.projection_digest != PROJECTION:
        raise ValueError("frozen PM2 projection identity differs")
    source_inputs = [inputs(view, scope) for scope in SCOPES]
    with TemporaryDirectory() as temp:
        profile = Path(temp) / "profile.json"
        profile.write_text(json.dumps(
            {"provider": provider, "device": args.device, "assets": str(args.assets.resolve())}
        ))
        with open_pm2_worker(
            python=python, script=PROVIDER_SCRIPT, profile=profile, device=args.device,
            nemotron_endpoint=settings.nemotron.endpoint if args.device == "cuda" else None,
        ) as worker:
            print(json.dumps({"startup": worker.startup}, ensure_ascii=False), flush=True)
            for scope, (mapping, tokens) in zip(SCOPES, source_inputs, strict=True):
                payload = run_request(provider, worker, mapping, tokens)
                payload["range"] = scope
                payload["text_digest"] = sha256(mapping.provider_text.encode()).hexdigest()
                print(json.dumps(payload, ensure_ascii=False), flush=True)
            oversized = {
                "d1": {
                    "state": {"source": "word " * 4053},
                    "questions": {"term": {"type": "text", "instructions": "Copy the first term."}},
                },
                "dipo": {"text": "word " * 2049},
                "hanlp": {"sentences": [["word"] * 129]},
                "maverick": {"sentences": [["word"] * 508]},
            }[provider]
            limit = worker.infer(oversized)
            if limit["outcome"] != "limited":
                raise ValueError("oversized request did not refuse")
            print(json.dumps({"oversized": limit}, ensure_ascii=False), flush=True)
            if provider == "d1":
                exact = {**oversized, "state": {"source": "word " * 4052}}
                accepted = worker.infer(exact)
                if accepted["row_tokens"] != [4096]:
                    raise ValueError("d1 did not execute the exact admitted token boundary")
                print(json.dumps({
                    "boundary": {"outcome": accepted["outcome"], "row_tokens": [4096]}
                }), flush=True)
                if args.cancel_d1:
                    child_pid = worker.pid
                    deadline = monotonic() + 0.05

                    def cancel():
                        if monotonic() > deadline:
                            raise InterruptedError("bounded d1 cancellation control")

                    try:
                        worker.infer(exact, check_active=cancel)
                    except InterruptedError:
                        if Path(f"/proc/{child_pid}").exists():
                            raise ValueError("cancelled d1 worker has not been reaped")
                    else:
                        raise ValueError("native cancellation control did not interrupt a request")
        if args.cancel_d1:
            endpoint = settings.nemotron.endpoint.rstrip("/").removesuffix("/v1")
            reply = httpx.get(f"{endpoint}/is_sleeping", timeout=10)
            reply.raise_for_status()
            if reply.json().get("is_sleeping") is not False:
                raise ValueError("Nemotron did not return awake after cancellation")
            print(json.dumps({"cancelled": {"child_reaped": True, "nemotron_awake": True}}))



if __name__ == "__main__":
    main()
