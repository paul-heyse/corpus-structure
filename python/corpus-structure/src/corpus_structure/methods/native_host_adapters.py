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
    project = root
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
        metadata, infer = _spacy(profile, assets)
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
        GlinerReport,
        BOUNDARY_DIAGNOSTIC,
        _json,
        _digest,
        boundary_diagnostic,
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
        if request.get("diagnostic") is not None:
            diagnostic = request["diagnostic"]
            if len(inputs) != 1:
                raise ValueError("diagnostic requires one exact source context")
            item, preparation = inputs[0], preparations[0]
            started = time.monotonic()
            raw = boundary_diagnostic(model, schema, item, preparation, tuple(tuple(pair) for pair in diagnostic["supplied"]))
            report = GlinerReport(item.context_id, item.context_digest, _digest(dict(operation=BOUNDARY_DIAGNOSTIC, context=item.context_digest, text=item.text, source_map=diagnostic["source_map_digest"], profile=selected.fingerprint, effective_profile=effective_profile_fingerprint(effective), pack=pack.fingerprint, supplied=diagnostic["supplied"])), selected.fingerprint, pack.fingerprint, preparation, _json({**raw, "source_map_digest": diagnostic["source_map_digest"]}), effective, time.monotonic()-started, reused, diagnostics=(("proposal_pool", "native_diagnostic"),))
            reused = True
            return {"reports": [asdict(report)]}
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


def _spacy(profile, assets):
    import spacy
    from spacy.tokens import Doc
    from hashlib import sha256

    parameters = profile["parameters"]
    spacy.require_gpu(0)
    nlp = spacy.load(parameters["model"], exclude=parameters["exclude"])
    import cupy
    parameters_seen = 0
    for _name, component in nlp.pipeline:
        model = getattr(component, "model", None)
        if model is None:
            continue
        for node in model.walk():
            for name in node.param_names:
                if node.has_param(name):
                    value = node.get_param(name)
                    if not isinstance(value, cupy.ndarray) or value.dtype != cupy.float32:
                        raise RuntimeError("spaCy resident parameter differs from CUDA FP32")
                    parameters_seen += 1
    if not parameters_seen:
        raise ValueError("learned spaCy profile has no resident GPU parameters")
    if spacy.__version__ != parameters["spacy_version"] or nlp.meta["version"] != parameters["model_version"]:
        raise ValueError("spaCy native package/model differs from frozen profile")
    from corpus_structure.methods.native_profiles import spacy_artifacts
    if spacy_artifacts(assets) != profile["artifacts"]:
        raise ValueError("spaCy model files differ from frozen profile")
    digest = sha256(nlp.config.to_str().encode()).hexdigest()

    def infer(request):
        if request.get("version") != "spacy-host-1":
            raise ValueError("unsupported spaCy host request")
        population = request["documents"]
        if not isinstance(population, list) or not 1 <= len(population) <= parameters["batch_size"]:
            raise ValueError("spaCy native batch exceeds declared population")
        docs = []
        for item in population:
            docs.append(Doc(nlp.vocab).from_bytes(base64.b64decode(item["content"], validate=True)))
        result = []
        originals = [(doc.text, len(doc)) for doc in docs]
        for original, doc in zip(originals, nlp.pipe(docs, batch_size=parameters["batch_size"], n_process=1), strict=True):
            if (doc.text, len(doc)) != original:
                raise RuntimeError("spaCy changed prepared source layout")
            result.append(base64.b64encode(doc.to_bytes()).decode("ascii"))
        return {"documents": result}

    return dict(dtype="torch.float32", device="cuda", backend="cupy", pipeline_sha256=digest, native_configuration=nlp.config.to_str(), components=[dict(name=name, factory=nlp.get_pipe_meta(name).factory) for name in nlp.pipe_names]), infer
