"""Source-only native v2 interface and warm request cancellation control.

Imports that can load model libraries are confined to execute(). --help is stdlib-only.
No reference, target, prediction, or grading artifact is consumed by this runner.
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict
from hashlib import sha256
import importlib.metadata
import json
import os
from pathlib import Path
import threading
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
POLICY = "m1-canonical-related-context-candidates-6"
PROFILE = "gliner2-2.1.0-cpu-fp32-standard-codepoints-v1"
CANCEL_AFTER_SECONDS = 0.5
SETTLEMENT_BOUND_SECONDS = 10.0


def digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, separators=(",", ":"),
                             allow_nan=False).encode()).hexdigest()


def file_receipt(path):
    blob = path.read_bytes()
    return dict(path=str(path), bytes=len(blob), sha256=sha256(blob).hexdigest())


def dump(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def append(path, value):
    with path.open("a") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n")


def proc(pid):
    fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
    return dict(pid=pid, start_ticks=int(fields[19]), state=fields[0],
                cpu_seconds=(int(fields[11]) + int(fields[12])) / os.sysconf("SC_CLK_TCK"),
                threads=int(fields[17]))


def absent(identity):
    try:
        current = proc(identity["pid"])
    except FileNotFoundError:
        return True
    return current["start_ticks"] != identity["start_ticks"]


def frozen_file(dataset, manifest, relative):
    path = dataset / relative
    key = f"{dataset.name}/{relative}"
    declared = [row for row in manifest["files"] if row["path"] == key]
    if len(declared) != 1:
        raise ValueError(f"frozen source input absent/ambiguous: {key}")
    actual = file_receipt(path)
    if any(actual[name] != declared[0][name] for name in ("bytes", "sha256")):
        raise ValueError(f"frozen source input changed: {key}")
    return path, actual


def load_sources(dataset):
    """Only whitelisted source/config/preparation bytes; never training target files."""
    freeze_path = dataset / "source-whitelist-freeze.json"
    freeze = json.loads(freeze_path.read_text())
    if freeze.get("outcome") != "passed" or freeze.get("immutable_scope") != "source-whitelist-only":
        raise ValueError("passed immutable source-only preparation whitelist required")
    names = ("contextual-configuration.json", "source-contexts.jsonl", "native-preparation.jsonl",
             "source-receipts.json", "launch.json")
    paths, receipts = {}, [file_receipt(freeze_path)]
    for name in names:
        paths[name], receipt = frozen_file(dataset, freeze, name)
        receipts.append(receipt)
    configuration = json.loads(paths["contextual-configuration.json"].read_text())
    if configuration["params"]["policy"] != POLICY:
        raise ValueError("this runner requires frozen policy6 source preparation")
    contexts = {}
    for line in paths["source-contexts.jsonl"].read_text().splitlines():
        row = json.loads(line)
        key = row["source_view_id"], row["index"]
        if (key in contexts or sha256(row["text"].encode()).hexdigest() != row["text_sha256"]
                or len(row["text"]) > 4096 or len(row["intervals"]) > 128):
            raise ValueError("duplicate or corrupt exact source context")
        contexts[key] = row
    preparations = []
    for line in paths["native-preparation.jsonl"].read_text().splitlines():
        row = json.loads(line)
        if (row["preparation_only"] is not True or row["supervised_targets"] is not False
                or row["build_targets"] is not False or row["actual_truncation"] is not False
                or row["native_cap_inactive"] is not True or row["exact_conditioning"] is not True
                or row["strict_capacity"] != 64 or row["on_capacity_exceeded"] != "raise"):
            raise ValueError("source-only untruncated preparation required")
        if any(sample.get("expected_records") or sample.get("expected") for sample in row["samples"]):
            raise ValueError("source preparation contains supervision")
        if row.get("record_mask") is not None or row.get("field_mask") is not None:
            raise ValueError("source preparation contains target masks")
        native = dict(encoding=row["conditioning"], record_specs=row["record_specs"])
        if row.get("payload_format") == "m1-fixed-schema-native-targets-experiment-2":
            native["original_schemas"] = row["original_schemas"]
        if (digest(native) != row["full_conditioning_digest"]
                or digest(row["conditioning"]) != row["conditioning_digest"]):
            raise ValueError("native full conditioning identity changed")
        source, index, family, variant = row["request"].split(":")
        sample, = row["samples"]
        if sample["sample_id"] != row["request"] or sample["family"] != family or sample["source"] != int(source):
            raise ValueError("source-only preparation sample binding differs from request")
        context = contexts[int(source), int(index)]
        if family not in context["selection"]["families"]:
            raise ValueError("request family absent from source-only selection")
        ids, = row["conditioning"]["input_ids"]
        words, = row["source_word_counts"]
        if not 0 < len(ids) <= 4096 or not 0 < words <= 4096:
            raise ValueError("source preparation violates existing 4096 bounds")
        if family in {"definition", "assertion"}:
            preparations.append(dict(request=row["request"], family=family, variant=variant,
                subwords=len(ids), words=words, source_bytes=len(context["text"].encode()),
                context=context, preparation=row))
    selected = {}
    for family in ("definition", "assertion"):
        eligible = [row for row in preparations if row["family"] == family]
        if not eligible:
            raise ValueError(f"no admitted source-only {family} input")
        selected[family] = max(eligible, key=lambda row: (
            row["subwords"], row["source_bytes"], row["request"]))
    return configuration, selected, receipts, json.loads(paths["source-receipts.json"].read_text()), json.loads(paths["launch.json"].read_text()), freeze


def check_report(report, selected, pack, profile, reused):
    effective = json.loads(report.effective_profile_json)
    if (effective["splitter"] != "UnicodeCodepointSplitter" or effective["device"] != "cpu"
            or effective["dtype"] != "float32" or effective["threads"] != 4
            or effective["interop_threads"] != 1):
        raise ValueError("actual child execution differs from CPU FP32 codepoint profile")
    context = selected["context"]
    if (report.context_id != context["context_id"] or report.context_digest != context["context_id"]
            or report.pack != pack.fingerprint or report.profile != profile.fingerprint
            or report.resident_reused is not reused):
        raise ValueError("native report request/profile/residency binding mismatch")
    if (report.preparation.consumed_text != context["text"] + report.preparation.synthetic_suffix
            or report.preparation.words != selected["words"]
            or report.preparation.subwords != selected["subwords"]):
        raise ValueError("actual consumed input differs from frozen source-only preparation")


def cancel_warm(worker, pack, item, out):
    """Use only the existing callback seam, with no inference-phase instrumentation."""
    identity = proc(worker.pid)
    serial = worker._serial  # Read-only observation of existing dispatch identity.
    started = time.monotonic()
    callbacks = []
    raised_at = None

    def check_active():
        nonlocal raised_at
        row = dict(elapsed=time.monotonic() - started, child=proc(identity["pid"]),
                   dispatch_serial=worker._serial,
                   ipc_thread_present=any(t.name == "gliner-ipc" and t.is_alive()
                                          for t in threading.enumerate()))
        callbacks.append(row)
        append(out / "cancellation-callbacks.jsonl", row)
        if row["elapsed"] >= CANCEL_AFTER_SECONDS:
            raised_at = time.monotonic()
            raise asyncio.CancelledError("predeclared warm native request cancellation control")

    try:
        reports = worker.extract(pack, (item,), threshold=0.5, check_active=check_active)
    except asyncio.CancelledError as error:
        caught_at = time.monotonic()
        pending = [row for row in callbacks if row["dispatch_serial"] == serial + 1
                   and row["ipc_thread_present"]]
        result = dict(outcome="observed", cancellation_type=type(error).__name__, notes=getattr(error, "__notes__", []),
            cancellation_after_seconds=CANCEL_AFTER_SECONDS, callbacks=callbacks,
            teardown_seconds=caught_at - raised_at if raised_at is not None else None,
            closed=worker.closed, child_identity=identity, child_absent=absent(identity),
            owner_pid_after=worker.pid,
            ipc_thread_absent=not any(t.name == "gliner-ipc" and t.is_alive() for t in threading.enumerate()),
            cpu_growth_seconds=max((row["child"]["cpu_seconds"] - identity["cpu_seconds"]
                                    for row in pending), default=0),
            dispatch_serial_before=serial,
            phase="warm owned request awaiting reply; child internal native phase unobservable",
            dispatch_limit="serial and live IPC thread show request exchange started, not send acknowledgement",
            scope="callback cancellation and owned child/IPC teardown; no distributed pipeline or model quality claim")
        passed = not (not pending or result["cpu_growth_seconds"] <= 0 or not result["closed"]
                or not result["child_absent"] or result["owner_pid_after"] is not None
                or not result["ipc_thread_absent"] or result["teardown_seconds"] > SETTLEMENT_BOUND_SECONDS)
        result["outcome"] = "passed" if passed else "partial"
        dump(out / "cancellation.json", result)
        if not passed:
            raise RuntimeError("warm active request cancellation observations/settlement incomplete")
        return result
    else:
        dump(out / "cancellation-completed-before-control.json", [asdict(r) for r in reports])
        raise RuntimeError("request completed before cancellation control; interruption not demonstrated")


def execute(args):
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", CUDA_VISIBLE_DEVICES="",
        TOKENIZERS_PARALLELISM="false", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    from corpus_structure.methods.gliner import GlinerInput
    from corpus_structure.methods.gliner_worker import GlinerWorker
    from corpus_structure.methods.m1_source import M1Config, configured_pack_variants
    from corpus_structure.orchestrate.m1 import registry
    from corpus_structure.semantic.regeneration import prepare_pack

    out = HERE / args.attempt
    out.mkdir(exist_ok=False)
    out.joinpath("executed-runner.py.txt").write_bytes(Path(__file__).read_bytes())
    dump(out / "launch.json", dict(pid=os.getpid(), identity=proc(os.getpid()), arguments=vars(args),
         cancellation_delay_seconds=CANCEL_AFTER_SECONDS, settlement_bound_seconds=SETTLEMENT_BOUND_SECONDS))
    worker = None
    identity = None
    started = time.monotonic()
    try:
        configuration, selected, receipts, source_receipts, launch, freeze = load_sources(Path(args.dataset).resolve())
        if (launch["run_id"] != args.source_run_id or freeze["run_id"] != args.source_run_id
                or freeze["cut_id"] != args.source_cut_id or freeze["release_id"] != args.release_id):
            raise ValueError("frozen source preparation run/cut/release differs from explicit current binding")
        for row in source_receipts["repository"]:
            path = Path(row["path"])
            if path.name in {"m1_source.py", "source_preparation.py", "record_packs.py", "gliner.py"}:
                actual = file_receipt(path)
                if any(actual[k] != row[k] for k in ("bytes", "sha256")):
                    raise ValueError(f"consumed source changed since preparation: {path}")
        for name, version in source_receipts["packages"].items():
            if importlib.metadata.version(name) != version:
                raise ValueError(f"native package changed: {name}")
        cfg = registry(ROOT / "domains/statistics").config("extract.m1_candidates", "contextual").config
        if not isinstance(cfg, M1Config) or cfg.model_dump(mode="json") != configuration["params"]:
            raise ValueError("current named contextual configuration differs from frozen preparation")
        registry_receipt = file_receipt(ROOT / "domains/statistics/m1-methods.yaml")
        if any(registry_receipt[k] != configuration["registry"][k] for k in ("bytes", "sha256")):
            raise ValueError("named registry bytes changed")
        profile = cfg.profile()
        if (profile.fingerprint != configuration["profile_fingerprint"] or profile.version != PROFILE
                or profile.max_words != 4096 or profile.max_subwords != 4096
                or cfg.max_context_chars != 4096 or cfg.max_context_pieces != 128
                or cfg.threshold != 0.5):
            raise ValueError("existing contextual execution profile/bounds changed")
        profile.verify_artifacts()
        _, _, _, prepared = prepare_pack(ROOT / "domains/statistics")
        if prepared.release_id != args.release_id:
            raise ValueError("current prepared release differs from explicit stable release")
        variants = configured_pack_variants(prepared, cfg)
        packs = {}
        for family, entry in selected.items():
            _, _, pack = next(row for row in variants[family] if row[0] == entry["variant"])
            declaration = json.loads(pack.declaration_json)
            frozen_pack = entry["preparation"]
            if (pack.version != "native-combined-v2" or frozen_pack["native_pack_version"] != pack.version
                    or frozen_pack["pack_fingerprint"] != pack.fingerprint
                    or frozen_pack["released_schema"] != declaration
                    or frozen_pack["original_schemas"] != [pack.compile().build()]):
                raise ValueError("actual v2 schema differs from source-only native preparation")
            structure = declaration["structures"][family]
            if family == "definition":
                field = next(f for f in structure["fields"] if f["name"] == "defining_text")
                if field["dtype"] != "list" or field["cardinality"] != "zero_or_more":
                    raise ValueError("definition-list frontend missing")
            elif structure["mode"] != "latent" or "anchor" in structure:
                raise ValueError("native latent assertion frontend missing")
            packs[family] = pack
        dump(out / "source-inputs.json", dict(release_id=prepared.release_id, source_run_id=args.source_run_id,
            source_cut_id=args.source_cut_id, source_whitelist=freeze,
            preparation_launch=launch, configuration=configuration, selected=selected, consumed_files=receipts,
            selection="all source-only admitted requests per family; largest subwords then source bytes then request ID; no target eligibility",
            profile={**asdict(profile), "snapshot": str(profile.snapshot)},
            packs={family: dict(fingerprint=pack.fingerprint, declaration=json.loads(pack.declaration_json))
                   for family, pack in packs.items()}))
        if args.preflight_only:
            result = dict(outcome="passed", mode="preflight-only", release_id=prepared.release_id,
                source_run_id=args.source_run_id, source_cut_id=args.source_cut_id,
                profile=profile.fingerprint, worker_created=False, model_loaded=False,
                selection={family: {key: entry[key] for key in ("request", "subwords", "words", "source_bytes")}
                           for family, entry in selected.items()},
                scope="complete frozen source/config/release/raw-pack/native-schema preflight; no model invocation")
            dump(out / "preflight.json", result)
            print(json.dumps(result), flush=True)
            return
        worker = GlinerWorker(profile)
        summaries = []
        for ordinal, family in enumerate(("definition", "definition", "assertion")):
            entry = selected[family]
            context = entry["context"]
            item = GlinerInput(context["context_id"], context["context_id"], context["text"])
            report, = worker.extract(packs[family], (item,), threshold=cfg.threshold)
            current = proc(worker.pid)
            if identity is None:
                identity = current
            if current["pid"] != identity["pid"] or current["start_ticks"] != identity["start_ticks"]:
                raise ValueError("resident child identity changed")
            dump(out / f"native-{ordinal + 1:02d}-{family}.json", asdict(report))
            check_report(report, entry, packs[family], profile, ordinal > 0)
            summaries.append(dict(family=family, request=entry["request"], child=current,
                inference_seconds=report.inference_seconds, resident_reused=report.resident_reused,
                subwords=report.preparation.subwords, words=report.preparation.words))
        family = max(selected, key=lambda f: (selected[f]["subwords"], selected[f]["source_bytes"], f))
        context = selected[family]["context"]
        dump(out / "cancellation-input.json", dict(family=family, request=selected[family]["request"],
             context_id=context["context_id"], pack=packs[family].fingerprint))
        cancellation = cancel_warm(worker, packs[family], GlinerInput(context["context_id"],
            context["context_id"], context["text"]), out)
        for receipt in receipts:
            current = file_receipt(Path(receipt["path"]))
            if any(current[k] != receipt[k] for k in ("bytes", "sha256")):
                raise ValueError("frozen source input changed during execution")
        profile.verify_artifacts()
        result = dict(outcome="passed", release_id=prepared.release_id, source_run_id=args.source_run_id,
            source_cut_id=args.source_cut_id,
            native_calls=summaries, cancellation=cancellation, wall_seconds=time.monotonic() - started,
            quality="not_established", adoption=False, training=False, labels_consumed=False,
            scope="v2 native definition-list/latent-assertion interfaces and warm owned request teardown only")
        dump(out / "summary.json", result)
        print(json.dumps(result), flush=True)
    except BaseException as error:
        dump(out / "failure.json", dict(outcome="failed", type=type(error).__name__, error=str(error),
             notes=getattr(error, "__notes__", []), traceback=traceback.format_exc()))
        raise
    finally:
        close_started = time.monotonic()
        try:
            if worker is not None:
                worker.close()
        finally:
            dump(out / "settlement.json", dict(closed=worker.closed if worker else None,
                owner_pid=worker.pid if worker else None, child_identity=identity,
                child_absent=absent(identity) if identity else None,
                ipc_thread_absent=not any(t.name == "gliner-ipc" and t.is_alive() for t in threading.enumerate()),
                close_seconds=time.monotonic() - close_started,
                external_process_tree_settlement="requires sampler wrapper exit and observed identity checks"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, help="selected passed immutable policy6 preparation attempt")
    parser.add_argument("--release-id", required=True, help="root-selected current prepared release")
    parser.add_argument("--source-run-id", required=True, type=int, help="completed retained source/annotation run")
    parser.add_argument("--source-cut-id", required=True, type=int, help="completed source/annotation final cut")
    parser.add_argument("--attempt", default="interface-002", help="new local output folder; never overwrite")
    parser.add_argument("--preflight-only", action="store_true", help="stop after every guard, before worker construction/model loading")
    args = parser.parse_args()
    if Path(args.attempt).name != args.attempt or not args.attempt.startswith("interface-") or args.attempt == "interface-001":
        parser.error("a new local interface-NNN output name other than frozen interface-001 is required")
    execute(args)


if __name__ == "__main__":
    main()
