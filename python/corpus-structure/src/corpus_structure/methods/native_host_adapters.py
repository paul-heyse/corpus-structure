"""Provider loaders for the two locked hosts; no database or orchestration state.

The host configures process-global state before calling these loaders. Adapters own
model-specific inference contexts and return only CPU-owned JSON values.
"""

from __future__ import annotations

import base64
import json
import os
import runpy
from dataclasses import asdict
from pathlib import Path


def load(declaration, torch):
    profile = declaration["profile"]
    provider = profile["provider"]
    assets = Path(declaration["assets"]).resolve(strict=True)
    root = Path(__file__).resolve().parents[5]
    project = root if provider in {"d1", "hanlp", "gliner", "spacy"} else root / "services/nlp-host-312"
    native = runpy.run_path(str(Path(__file__).with_name("pm2_native.py")))
    runtime = native["_runtime_identity"](provider, project=project)
    if runtime != profile["runtime_identity"]:
        raise ValueError("shared host runtime differs from frozen profile")
    if provider in {"d1", "hanlp", "maverick", "dipo"}:
        observed = native["_verify_assets"](assets, provider)
        if observed != profile["artifacts"]:
            raise ValueError("shared host artifacts differ from frozen profile")
        # All PM2 residents must use one host-global offline cache. The parent
        # declaration rejects conflicting cache roots before acquiring custody.
        if os.environ.get("HF_HUB_CACHE") != str(assets / "hub"):
            raise ValueError("host offline cache differs from declared assets")
        if provider == "d1":
            loader = native["_load_d1"]
        else:
            filename = "pm2_hanlp.py" if provider == "hanlp" else "pm2_dispatched.py"
            loader = runpy.run_path(str(Path(__file__).with_name(filename)))["load_" + provider]
        metadata, infer = loader(assets, "cuda")
        metadata["backend"] = metadata["attention_implementation"]
    elif provider == "gliner":
        metadata, infer = _gliner(profile, assets)
    elif provider == "spacy":
        metadata, infer = _spacy(profile)
    else:
        raise ValueError("unsupported shared native provider")
    if metadata["backend"] != profile["backend"]:
        raise ValueError("native backend differs from frozen profile")
    return {**metadata, "runtime_identity": runtime, "assets": profile["artifacts"]}, infer


def _gliner(profile, assets):
    from corpus_structure.methods.gliner import (
        GlinerInput,
        GlinerPack,
        GlinerProfile,
        effective_profile_fingerprint,
        load_model,
        prepare_input,
    )
    from corpus_structure.methods.model_observation import (
        batch_receipt,
        installed_policy,
        observation_digest,
        request_digest,
    )
    from corpus_structure.methods.gliner_worker import validate_request

    import time

    values = dict(profile["parameters"]["gliner_profile"])
    values["snapshot"] = assets
    values["artifact_hashes"] = tuple(tuple(entry) for entry in values["artifact_hashes"])
    selected = GlinerProfile(**values)
    if selected.device != "cuda" or dict(selected.artifact_hashes) != profile["artifacts"]:
        raise ValueError("GLiNER host requires matching explicit CUDA artifacts/profile")
    model, effective = load_model(selected, configure_process=False)
    reused = False

    def infer(request):
        nonlocal reused
        if request.get("version") != "gliner-host-1":
            raise ValueError("unsupported GLiNER host request")
        pack = GlinerPack(**request["pack"])
        inputs = tuple(GlinerInput(**value) for value in request["inputs"])
        threshold, overlap = request["threshold"], request["overlap_policy"]
        evaluation = request.get("evaluation", False)
        validate_request(selected, pack, inputs, threshold=threshold, overlap_policy=overlap, evaluation=evaluation)
        schema = pack.compile()
        preparations, admissions = [], []
        for ordinal, item in enumerate(inputs):
            try:
                preparation = prepare_input(model, schema, item, selected)
            except ValueError as error:
                if not request.get("prepare_only"):
                    raise
                admissions.append(dict(ordinal=ordinal, context_id=item.context_id, context_digest=item.context_digest, admitted=False, reason=str(error)[:1800]))
            else:
                preparations.append(preparation)
                admissions.append(dict(ordinal=ordinal, context_id=item.context_id, context_digest=item.context_digest, admitted=True, reason=None))
        if request.get("prepare_only"):
            return {"admissions": admissions}
        inference = installed_policy()[0]["inference"]
        settings = {key: value for key, value in inference.items() if key != "operation"}
        identity = request_digest(pack, asdict(selected), inputs, threshold, overlap, evaluation, inference)
        receipt = batch_receipt(pack, asdict(selected), inputs, threshold, overlap, evaluation, inference)
        started = time.monotonic()
        raw = model.batch_extract([item.text for item in inputs], schema, batch_size=len(inputs), threshold=threshold, overlap_policy=overlap, **settings)
        elapsed = time.monotonic() - started
        if len(raw) != len(inputs):
            raise RuntimeError("GLiNER native result population changed")
        reports = []
        for ordinal, (item, preparation, result) in enumerate(zip(inputs, preparations, raw, strict=True)):
            raw_json = json.dumps(result, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
            reports.append(dict(context_id=item.context_id, context_digest=item.context_digest, computation=identity, profile=selected.fingerprint, pack=pack.fingerprint, preparation=asdict(preparation), raw_json=raw_json, effective_profile_json=effective, inference_seconds=elapsed, resident_reused=reused, request_digest=identity, batch_receipt_json=json.dumps(receipt, ensure_ascii=False, separators=(",", ":"), allow_nan=False), member_ordinal=ordinal, observation_digest=observation_digest(identity, raw_json, effective, ordinal=ordinal, member=receipt["members"][ordinal])))
        reused = True
        return {"reports": reports}

    return dict(dtype="torch.float32", device="cuda", backend="standard", effective_profile=effective_profile_fingerprint(effective)), infer


def _spacy(profile):
    import spacy
    from spacy.tokens import Doc
    from hashlib import sha256

    parameters = profile["parameters"]
    spacy.require_gpu(0)
    nlp = spacy.load(parameters["model"], exclude=parameters["exclude"])
    if spacy.__version__ != parameters["spacy_version"] or nlp.meta["version"] != parameters["model_version"]:
        raise ValueError("spaCy native package/model differs from frozen profile")
    digest = sha256(nlp.config.to_str().encode()).hexdigest()
    if digest != profile["artifacts"]["pipeline_sha256"]:
        raise ValueError("spaCy pipeline differs from frozen profile")

    def infer(request):
        if request.get("version") != "spacy-host-1":
            raise ValueError("unsupported spaCy host request")
        population = request["documents"]
        if not isinstance(population, list) or not 1 <= len(population) <= parameters["batch_size"]:
            raise ValueError("spaCy native batch exceeds declared population")
        docs = []
        for item in population:
            words, spaces = item["words"], item["spaces"]
            if len(words) != len(spaces) or any(type(value) is not str for value in words) or any(type(value) is not bool for value in spaces):
                raise ValueError("spaCy prepared layout is invalid")
            docs.append(Doc(nlp.vocab, words=words, spaces=spaces))
        result = []
        for original, doc in zip(docs, nlp.pipe(docs, batch_size=parameters["batch_size"], n_process=1), strict=True):
            if doc.text != original.text or len(doc) != len(original):
                raise RuntimeError("spaCy changed prepared source layout")
            result.append(base64.b64encode(doc.to_bytes()).decode("ascii"))
        return {"documents": result}

    return dict(dtype="torch.float32", device="cuda", backend="cupy", pipeline_sha256=digest, components=[dict(name=name, factory=nlp.get_pipe_meta(name).factory) for name in nlp.pipe_names]), infer
