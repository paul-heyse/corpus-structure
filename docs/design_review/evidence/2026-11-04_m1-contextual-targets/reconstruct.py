"""Checked feature-fit reconstruction and native metadata only; never load a model.

Importing this module performs no reads or writes. Execution requires an explicitly
authorized completed run; failed or interrupted runs cannot satisfy the SQL capability.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PROCESSOR = HERE.parent / "2026-11-04_m1-fixed-schema-loss/fixed_schema_processor.py"
DENOMINATOR = {"definition": 14, "assertion": 56, "measurement": 32, "table": 80, "formula_context": 88}
POPULATION = {
    "version": "m1-contextual-target-population-experiment-1",
    "symbol_binding": "C symbol present, genuine exact symbol anchor, source-owned formula occurrence",
    "formula_reading": "all C readings for source-owned formula occurrence, including bindings",
    "native_formula_context": "selected primary native formula only; neighbors retained outside request population",
    "prose_formula_context": "exact formula in primary source; existing owned scope only",
    "conditioning_conflict": "identical model conditioning with different target sets refuses every conflicting example",
    "denominator": "all original270 C readings retained; request applicability never changes grading",
}


def digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def full_conditioning_digest(receipt):
    # Record specs select natural instance formation and constrained assignment.
    # Equal encoder tokens alone do not make symbol/formula anchor packs equal.
    return digest({"encoding": receipt["conditioning"], "record_specs": receipt["record_specs"]})


def file_receipt(path):
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": sha256(data).hexdigest()}


def write(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def append(path, value):
    # Field insertion order belongs to the native conditioning contract.
    with path.open("a") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n")


def load_wrapper():
    spec = importlib.util.spec_from_file_location("settled_m1_fixed_schema_processor", PROCESSOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def literal_anchors(record, role, usage="literal"):
    anchors = {row["anchor_id"]: row for row in record["anchors"]}
    fields = {row["role"]: row for row in record["fields"]}
    sets = {row["set_id"]: row for row in record["evidence_sets"]}
    return [anchors[key] for identity in fields[role].get("evidence_sets", ())
            if sets[identity]["usage"] == usage for key in sets[identity]["anchors"]]


def interval_pointer(interval):
    locator = json.loads(interval.item_locator.removeprefix("pdf:"))
    pointer = locator["pointer"]
    if interval.cell_index is not None and interval.source_field == "cell_text":
        pointer += f"/data/table_cells/{interval.cell_index}"
    return pointer


def original_to_actual(reference):
    return {row["reference_pin"]["source_view_id"]: row["prediction_pin"]["source_view_id"]
            for row in reference["prediction_binding"]["views"]}


def overlaps(context, anchors, correspondence):
    from corpus_structure.semantic.source_contexts import SourceInterval

    return any(isinstance(interval, SourceInterval)
               and interval.source.source_view_id == correspondence.get(anchor["pin"]["source_view_id"])
               and interval_pointer(interval) == anchor["pointer"]
               and interval.source_start < anchor["end"] and interval.source_end > anchor["start"]
               for anchor in anchors if anchor["space"] == "selected_projection" and anchor["precision"] == "exact"
               for interval in context.intervals)


def map_anchors(context, anchors, correspondence, prepared, processor):
    from gliner2.processing.targets import char_span_to_word_boundaries, word_boundaries_to_char_span
    from corpus_structure.semantic.source_contexts import SourceInterval

    ranges, expected = [], []
    for anchor in anchors:
        if anchor["space"] != "selected_projection" or anchor["precision"] != "exact":
            raise ValueError("literal/cue needs exact independently authored selected-projection anchors")
        actual_id = correspondence[anchor["pin"]["source_view_id"]]
        matches = []
        for interval in context.intervals:
            if (not isinstance(interval, SourceInterval)
                or interval.source.source_view_id != actual_id
                or interval_pointer(interval) != anchor["pointer"]
                or not interval.source_start <= anchor["start"] < anchor["end"] <= interval.source_end):
                continue
            start = interval.model_start + anchor["start"] - interval.source_start
            end = start + anchor["end"] - anchor["start"]
            if context.text[start:end] == anchor["source_piece"]:
                matches.append((start, end))
        if len(matches) != 1:
            raise ValueError("gold piece not uniquely present in bounded source context")
        ranges.append(matches[0])
        expected.append((actual_id, anchor["pointer"], anchor["start"], anchor["end"], anchor["source_piece"]))
    if not ranges:
        raise ValueError("present role has no independent exact literal/cue anchors")
    if ranges != sorted(ranges):
        raise ValueError("gold ordered pieces differ from context order")
    start, end = ranges[0][0], ranges[-1][1]
    reading = context.read_span(start, end, prepared=prepared, policy="synthetic-whitespace-1", literal=context.text[start:end])
    actual = [(piece.source.source_view_id, json.loads(piece.item_locator.removeprefix("pdf:"))["pointer"]
               + (f"/data/table_cells/{piece.cell_index}" if piece.cell_index is not None and piece.source_field == "cell_text" else ""),
               piece.start, piece.end, piece.quote) for piece in reading.pieces]
    if actual != expected:
        raise ValueError("scalar bounding span adds, removes, reorders or joins genuine source pieces")
    words = list(processor.word_splitter(context.text, lower=True))
    starts, ends = [row[1] for row in words], [row[2] for row in words]
    token_start, token_end = char_span_to_word_boundaries(start, end, starts, ends)
    if word_boundaries_to_char_span(token_start, token_end, starts, ends) != (start, end):
        raise ValueError("native word boundaries broaden original source span")
    reread = context.read_span(start, end, prepared=prepared, policy="synthetic-whitespace-1")
    if reread != reading:
        raise ValueError("source-token-source round trip changed source reading")
    return {"text": context.text[start:end], "start": start, "end": end}, {
        "reading": reading.receipt(), "source_pieces": expected, "word_span": [token_start, token_end]}


def map_record(record, context, pack, correspondence, prepared, processor):
    declaration = json.loads(pack.declaration_json)["structures"][record["family"]]
    gold = {row["role"]: row for row in record["fields"]}
    target, mappings, errors = {}, {}, []
    for field in declaration["fields"]:
        name = field["name"]
        role = name.removesuffix("__state").removesuffix("__cue")
        value = gold.get(role)
        try:
            if value is None:
                raise ValueError("released role absent from independent record")
            if name.endswith("__state"):
                if value["state"] not in field["choices"]:
                    raise ValueError("independent state outside released choices")
                target[name] = {"choices": field["choices"], "value": value["state"]}
            elif name.endswith("__cue"):
                anchors = literal_anchors(record, role, "classification_cue")
                if not anchors and value["state"] != "present":
                    target[name] = None
                else:
                    target[name], mappings[name] = map_anchors(context, anchors, correspondence, prepared, processor)
            elif field.get("choices"):
                if value["state"] != "present":
                    target[name] = None
                else:
                    label = value["value"]["label"]
                    if label not in field["choices"]:
                        raise ValueError("independent classification outside released choices")
                    target[name] = {"choices": field["choices"], "value": label}
            elif value["state"] != "present":
                target[name] = None
            else:
                target[name], mappings[name] = map_anchors(context, literal_anchors(record, role), correspondence, prepared, processor)
        except (ValueError, KeyError, TypeError) as error:
            errors.append({"role": name, "reason": str(error), "type": type(error).__name__})
    return target, mappings, errors


def scope_errors(context, reference):
    from corpus_structure.evaluate.record_alignment import anchor_in_scope
    from corpus_structure.semantic.source_contexts import SourceInterval, SyntheticInterval

    frame = reference["source_frame"]["evaluation_frame"]
    reverse = {row["prediction_pin"]["source_view_id"]: row["reference_pin"]
               for row in reference["prediction_binding"]["views"]}
    errors = []
    for index, interval in enumerate(context.intervals):
        if isinstance(interval, SyntheticInterval):
            continue
        if not isinstance(interval, SourceInterval) or interval.source.source_view_id not in reverse:
            errors.append({"interval": index, "reason": "real context interval outside independently annotated source closure"})
            continue
        descriptor = dict(anchor_id="", pin=reverse[interval.source.source_view_id], space="selected_projection",
                          pointer=interval_pointer(interval), precision="exact", start=interval.source_start, end=interval.source_end)
        if not anchor_in_scope(descriptor, frozenset(frame["anchor_ids"]), frame["anchor_scopes"]):
            errors.append({"interval": index, "reason": "real interval outside independent exact annotation scope", "descriptor": descriptor})
    return errors


def formula_population(record, selection, view, context, correspondence, prepared, processor, variant, population_mode):
    from corpus_structure.methods.m1_source import _formula_matches_primary, _prose_formula_scope

    if variant == "symbol_binding":
        symbol = next(row for row in record["fields"] if row["role"] == "symbol")
        if symbol["state"] != "present":
            return False, "symbol not independently present; outside binding training population"
        anchors = literal_anchors(record, "symbol")
        if not anchors or any(row["space"] != "selected_projection" or row["precision"] != "exact" for row in anchors):
            return False, "present symbol lacks independent exact anchor; population prerequisite unavailable"
    try:
        formula, _ = map_anchors(context, literal_anchors(record, "formula"), correspondence, prepared, processor)
    except (ValueError, KeyError, TypeError) as error:
        raise ValueError(f"formula population source mapping: {error}") from error
    node = next(row for row in view.items if row["self_ref"] == selection.region)
    group = {"formula": formula}
    if population_mode == "full-visible":
        if _prose_formula_scope(view, context, group) is None:
            return False, "decoder formula outside exact primary-source context"
        return True, None
    if node.get("label") == "formula":
        if not _formula_matches_primary(context, group, selection.region):
            return False, "neighbor formula outside selected native-primary structural population"
    elif _prose_formula_scope(view, context, group) is None:
        return False, "formula outside exact primary-source prose scope"
    return True, None


def structural_custody(record, selection, view, context, target, population_mode):
    """Authenticate nonextractive sidecars through existing source/geometry custody."""
    from corpus_structure.methods.m1_source import _formula_matches_primary, _prose_formula_scope, _structural_groups

    native = [field for field in record["fields"] if field["kind"] == "native"]
    actual = {}
    if record["family"] == "definition":
        actual["scope"] = view.ref.section_pointer
    elif record["family"] == "formula_context" and population_mode == "full-visible":
        source_scope = _prose_formula_scope(view, context, target)
        if source_scope is None:
            raise ValueError("decoder proposal lacks authenticated owned source scope")
        actual = {field.role: field.native_pointer for field in source_scope.fields if field.native_pointer is not None}
    elif record["family"] in {"formula_context", "table"}:
        groups = _structural_groups(view, selection, context)
        if record["family"] == "table":
            wanted = next(field["value"]["pointer"] for field in native if field["role"] == "cell")
            groups = tuple(group for group in groups if any(field.role == "cell" and field.native_pointer == wanted for field in group.fields))
        elif not groups:
            scope = _prose_formula_scope(view, context, target)
            groups = (scope,) if scope is not None else ()
        if len(groups) != 1:
            raise ValueError("native-only sidecar lacks one exact existing structural owner")
        actual = {field.role: field.native_pointer for field in groups[0].fields if field.native_pointer is not None}
    for field in native:
        if field["state"] != "present" or actual.get(field["role"]) != field["value"]["pointer"]:
            raise ValueError(f"native-only {field['role']} differs from independently authored structural location")
    normalized = [field for field in record["fields"] if field["kind"] == "normalized"]
    if any(field["state"] != "inapplicable" for field in normalized):
        raise ValueError("current source-inspection path supplies no numeric transformation")
    node = next(row for row in view.items if row["self_ref"] == selection.region)
    request_primary = (record["family"] != "formula_context" or node.get("label") != "formula"
                       or _formula_matches_primary(context, target, selection.region))
    return {"native_locations": actual, "normalized_policy": "source literals only; no numeric transformation",
            "gold_nonextractive_fields": native + normalized, "request_primary_assembly_eligible": request_primary,
            "scope_provenance": "existing owned source section; no native FormulaOccurrence invented",
            "actual_supplement_attached": False}


def inspect_widened_routes(out, ids, records, selection, view, context, packs, correspondence, prepared, wrapper, cfg, fixed, reference):
    """Counterfactual mapping only; never add routes or examples to the dataset."""
    if selection.families != ("formula_context",):
        return
    for family in ("definition", "assertion"):
        targeted = [record for record in records if record["record_id"] in ids and record["family"] == family]
        if not targeted:
            continue
        _, anchor_role, pack = packs[family][0]
        for record in targeted:
            if not overlaps(context, literal_anchors(record, anchor_role), correspondence):
                continue
            target, mappings, errors = map_record(record, context, pack, correspondence, prepared, wrapper.native)
            row = dict(record_id=record["record_id"], family=family, context_id=context.dependency_digest,
                selected_formula=selection.region, source_view_id=view.ref.id, context_chars=len(context.text),
                context_pieces=len(context.intervals), not_routed=True, mapping_complete=not errors,
                errors=errors, mapped_roles=list(mappings), scope_errors=scope_errors(context, reference),
                pack_fingerprint=pack.fingerprint, native_preparation=None, whole_family_errors=[])
            if not errors:
                declaration = json.loads(pack.declaration_json)
                payload = dict(format=wrapper.FORMAT, sample_id="routing-diagnostic", family=family, source=view.ref.id,
                    released_schema=declaration, released_schema_digest=fixed.digest(declaration),
                    target_records=[], target_records_digest=fixed.digest([]))
                try:
                    batch = wrapper.collate_fn_inference([(context.text, payload)], max_len=cfg.max_words,
                        build_targets=False, architecture="boundary", max_gold_per_query=64,
                        on_capacity_exceeded="raise", error_policy="raise")
                    assert batch.original_lengths[0] <= cfg.max_subwords, "schema-conditioned subword bound exceeded"
                    row["native_preparation"] = dict(admitted=True, source_words=wrapper.last_receipt["source_word_counts"][0],
                        prefix_words=wrapper.last_receipt["samples"][0]["prefix_length"], subwords=batch.original_lengths[0],
                        full_conditioning_digest=full_conditioning_digest(wrapper.last_receipt))
                except Exception as error:
                    row["native_preparation"] = dict(admitted=False, reason=str(error), type=type(error).__name__)
                anchors = defaultdict(list)
                for neighbor in records:
                    if neighbor["family"] != family or not overlaps(context, literal_anchors(neighbor, anchor_role), correspondence):
                        continue
                    neighbor_target, _, neighbor_errors = map_record(neighbor, context, pack, correspondence, prepared, wrapper.native)
                    if neighbor_errors:
                        row["whole_family_errors"].append(dict(record_id=neighbor["record_id"], errors=neighbor_errors))
                    else:
                        anchor = neighbor_target[anchor_role]
                        anchors[anchor["start"], anchor["end"]].append(neighbor["record_id"])
                row["natural_anchor_collisions"] = [values for values in anchors.values() if len(values) > 1]
            append(out / "routing-diagnostic.jsonl", row)


def metadata_reports(conn, task_id):
    """SQL projection whitelists preparation only; no predicted groups enter Python."""
    from sqlalchemy import text
    from corpus_structure.semantic.observations import source_python

    q = text("""SELECT r.ordinality, f->>'name' AS name,f->'value' AS value
      FROM ops.task_result tr CROSS JOIN LATERAL jsonb_array_elements(tr.body->'parse_detail'->'fields') d
      CROSS JOIN LATERAL jsonb_array_elements(d->'value'->'items') WITH ORDINALITY r(value,ordinality)
      CROSS JOIN LATERAL jsonb_array_elements(r.value->'fields') f
      WHERE tr.task_id=:task AND d->>'name'='reports'
      AND f->>'name' IN ('context','family','variant','anchor_role','operation')""")
    out = {}
    for row in conn.execute(q, {"task": task_id}).mappings():
        out.setdefault(row["ordinality"], {})[row["name"]] = source_python(row["value"])
    q = text("""SELECT r.ordinality, f->>'name' AS name,f->'value' AS value
      FROM ops.task_result tr CROSS JOIN LATERAL jsonb_array_elements(tr.body->'parse_detail'->'fields') d
      CROSS JOIN LATERAL jsonb_array_elements(d->'value'->'items') WITH ORDINALITY r(value,ordinality)
      CROSS JOIN LATERAL jsonb_array_elements(r.value->'fields') rf
      CROSS JOIN LATERAL jsonb_array_elements(rf->'value'->'fields') f
      WHERE tr.task_id=:task AND d->>'name'='reports' AND rf->>'name'='report'
      AND f->>'name' IN ('context_id','context_digest','pack','preparation','effective_profile_ref')""")
    for row in conn.execute(q, {"task": task_id}).mappings():
        out.setdefault(row["ordinality"], {})[row["name"]] = source_python(row["value"])
    return [out[key] for key in sorted(out) if "pack" in out[key]]


def source_metadata(conn, task_id):
    from sqlalchemy import text
    from corpus_structure.semantic.observations import source_python

    rows = conn.execute(text("""SELECT f->>'name' AS name,f->'value' AS value
      FROM ops.task_result tr CROSS JOIN LATERAL jsonb_array_elements(tr.body->'parse_detail'->'fields') f
      WHERE tr.task_id=:task AND f->>'name' IN ('contexts','annotation_product','effective_profiles')"""),
      {"task": task_id}).mappings()
    return {row["name"]: source_python(row["value"]) for row in rows}


def main(args):
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", TOKENIZERS_PARALLELISM="false",
                      CUDA_VISIBLE_DEVICES="", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    import torch
    from gliner2.processor import SchemaTransformer
    from sqlalchemy import text
    from transformers import AutoTokenizer
    from corpus_structure.evaluate.record_references import read_fitting_references
    from corpus_structure.ingest.annotations import AnnotationProfile
    from corpus_structure.methods.gliner import CODEPOINT_PROFILE, UnicodeCodepointSplitter
    from corpus_structure.methods.m1_annotations import consume_annotations
    from corpus_structure.methods.m1_source import M1Config, configured_pack_variants
    from corpus_structure.methods.source_preparation import POLICY_V5, prepare_source
    from corpus_structure.orchestrate.m1 import registry
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.operations import BoundReader
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.record_contracts import anchor_identity, evidence_set_identity
    from corpus_structure.semantic.releases import open_release
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.settings import Settings

    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    population = dict(POPULATION)
    if args.population_mode == "full-visible":
        population.update(version="m1-contextual-target-population-experiment-2",
            symbol_binding="C symbol present with genuine exact anchor; all fully located decoder readings visible in context",
            formula_reading="all fully located C decoder readings visible in context, including bindings and neighbor formulas",
            native_formula_context="selected-primary custody is assembly-only; decoder population includes located neighbors",
            structural_sidecar="authenticate owned source scope without claiming an actual primary supplement or publication")
    out = HERE / args.attempt
    out.mkdir(exist_ok=False)
    write(out / "launch.json", {"at": datetime.now(timezone.utc).isoformat(), "run_id": args.run_id,
          "source": file_receipt(Path(__file__)), "processor": file_receipt(PROCESSOR), "population": population,
          "scope": "protected set1 and native metadata only; no model/forward/training"})
    (out / "reconstruct-executed.py.txt").write_bytes(Path(__file__).read_bytes())
    (out / "fixed_schema_processor-executed.py.txt").write_bytes(PROCESSOR.read_bytes())
    try:
        assert importlib.metadata.version("gliner2") == "2.1.0"
        registry_path = REPO / "domains/statistics/m1-methods.yaml"
        contextual_params = registry(registry_path.parent).file.configs["extract.m1_candidates"]["contextual"]
        contextual_cfg = M1Config.model_validate(contextual_params)
        configuration = dict(origin="native named statistics registry; independent of model predictions",
            name="extract.m1_candidates/contextual", registry=file_receipt(registry_path),
            params=contextual_cfg.model_dump(mode="json"),
            config_digest=sha256(canonical_bytes(contextual_cfg.model_dump(mode="json"))).hexdigest(),
            profile=asdict(contextual_cfg.profile()))
        configuration["profile"]["snapshot"] = str(contextual_cfg.snapshot)
        configuration["profile_fingerprint"] = contextual_cfg.profile().fingerprint
        write(out / "contextual-configuration.json", configuration)
        (out / "m1-methods-executed.yaml.txt").write_bytes(registry_path.read_bytes())
        source_modules = ["methods/m1_source.py", "methods/source_preparation.py", "methods/record_packs.py",
            "methods/gliner.py", "methods/m1_annotations.py", "methods/record_assembly.py",
            "semantic/source_contexts.py", "evaluate/record_references.py", "semantic/sql/record_references.sql"]
        source_root = REPO / "python/corpus-structure/src/corpus_structure"
        source_receipts = [file_receipt(source_root / p) for p in source_modules]
        write(out / "source-receipts.json", dict(repository=source_receipts,
            packages={name: importlib.metadata.version(name) for name in
                ("gliner2", "torch", "transformers", "tokenizers", "safetensors")},
            scope="exact source and configuration inspected by this reconstruction; no model checkpoint modified"))
        snapshots = out / "executed-source"
        snapshots.mkdir()
        for relative in source_modules:
            (snapshots / (relative.replace("/", "__") + ".txt")).write_bytes((source_root / relative).read_bytes())
        with open_runtime_engine(Settings(), "m1-contextual-targets-fit", purpose="fit") as engine, read_snapshot(engine) as conn:
            refs = read_fitting_references(conn, 1, prediction_run_id=args.run_id)
        assert [row["pass_id"] for row in refs] == [23, 24]
        assert all(row["sampling"]["partition"] == "feature_fit" for row in refs)
        assert dict(Counter(r["family"] for u in refs for r in u["authored"]["records"])) == DENOMINATOR
        write(out / "feature-fit-protected.json", refs)
        applicability = refs[0]["applicability"]
        assert all(row["applicability"] == applicability for row in refs)
        assert applicability["run_id"] == args.run_id
        states, ledger, proposals = {}, {}, []
        all_conditioning_audits = defaultdict(list)
        diagnostic_ids = set()
        if args.routing_diagnostic:
            baseline_ledger = [json.loads(line) for line in (HERE / "attempt-001/record-disposition.jsonl").read_text().splitlines()]
            diagnostic_ids = {entry["record_id"] for entry in baseline_ledger if entry["family"] in {"definition", "assertion"} and not entry["mapped_requests"]}
            assert len(diagnostic_ids) == 10
            write(out / "routing-diagnostic-inputs.json", dict(record_ids=sorted(diagnostic_ids),
                baseline=file_receipt(HERE / "attempt-001/record-disposition.jsonl"),
                scope="mapping-only of existing formula-only source-generated neighborhoods; no route/profile/schema change"))
        request_counts = Counter()
        for reference in refs:
            for record in reference["authored"]["records"]:
                assert all(anchor_identity(row) == row["anchor_id"] for row in record["anchors"])
                assert all(evidence_set_identity(row) == row["set_id"] for row in record["evidence_sets"])
                ledger[record["record_id"]] = dict(record_id=record["record_id"], family=record["family"],
                    pass_id=reference["pass_id"], content_digest=reference["content_digest"], original_pin=record["pin"],
                    roles=[dict(role=f["role"], state=f["state"], kind=f["kind"], evidence_sets=f.get("evidence_sets", [])) for f in record["fields"]],
                    mapped_requests=[], excluded_requests=[], outside_population=[], emitted_requests=[],
                    assembly_exclusions=[])
                if record["family"] == "formula_context":
                    by_role = {row["role"]: row for row in record["fields"]}
                    ledger[record["record_id"]]["pack_population"] = dict(
                        symbol_state_present=by_role["symbol"]["state"] == "present",
                        requires_exact_symbol_and_request_formula_custody=True,
                        formula_reading=True,
                        rule=population["version"])
                    if (by_role["symbol"]["state"], by_role["meaning"]["state"]) not in {("present", "present"), ("unstated", "unstated")}:
                        ledger[record["record_id"]]["assembly_exclusions"].append("current formula occurrence adapter requires both symbol/meaning present or both unstated")
        fixed = load_wrapper()
        with open_runtime_engine(Settings(), "m1-contextual-targets-source", purpose="read") as engine, read_snapshot(engine) as conn:
            prepared = open_release(conn, applicability["prediction_release_id"])
            reader = BoundReader(conn, args.run_id, prepared, applicability["cut_id"], analysis=False)
            for reference in refs:
                source_id = reference["prediction_binding"]["prediction_frame"]["evaluation_frame"]["pin"]["source_view_id"]
                row = conn.execute(text("""SELECT t.id,t.input_hash,t.reused_task_id,c.params,c.config_hash
                  FROM ops.task t JOIN ops.method_config c ON c.id=t.method_config_id
                  JOIN ops.method m ON m.id=c.method_id
                  WHERE t.run_id=:run AND t.unit_id=:source AND m.name='extract.m1_candidates'"""),
                  {"run": args.run_id, "source": source_id}).mappings().one_or_none()
                cfg = contextual_cfg
                if row is not None:
                    assert canonical_bytes(M1Config.model_validate(row["params"]).model_dump(mode="json")) == canonical_bytes(cfg.model_dump(mode="json"))
                assert cfg.policy == POLICY_V5 and cfg.execution_profile == CODEPOINT_PROFILE and cfg.source_inspection
                assert cfg.max_words == cfg.max_subwords == cfg.max_context_chars == 4096
                assert cfg.max_context_pieces == 128 and cfg.formula_prose
                cfg.profile().verify_artifacts()
                checkpoint = json.loads((cfg.snapshot / "config.json").read_text())
                max_gold = checkpoint["boundary_head"]["max_gold_per_query"]
                assert max_gold == 64
                key = str(cfg.snapshot)
                if key not in states:
                    tokenizer = AutoTokenizer.from_pretrained(str(cfg.snapshot), local_files_only=True)
                    native = SchemaTransformer(tokenizer=tokenizer, word_splitter=UnicodeCodepointSplitter())
                    assert type(native.word_splitter) is UnicodeCodepointSplitter
                    states[key] = fixed.FixedSchemaProcessor(native, max_gold_per_query=max_gold)
                wrapper = states[key]
                view = reader.source_view(source_id)
                profile = AnnotationProfile(cfg.sentences)
                annotations, annotation_errors, annotation_result = consume_annotations(reader, view, profile)
                product = prepare_source(view, profile=profile, max_chars=cfg.max_context_chars,
                    max_pieces=cfg.max_context_pieces, max_annotation_chars=cfg.max_annotation_chars,
                    reader=reader, persisted_annotations=annotations, annotation_errors=annotation_errors,
                    policy=cfg.policy, formula_prose=cfg.formula_prose)
                packs = configured_pack_variants(prepared, cfg)
                actual_task = (row["reused_task_id"] or row["id"]) if row is not None else None
                reports = metadata_reports(conn, actual_task) if actual_task is not None else []
                source_meta = source_metadata(conn, actual_task) if actual_task is not None else {}
                annotation_digest = sha256(canonical_bytes(annotation_result)).hexdigest()
                if source_meta:
                    assert canonical_bytes(source_meta["contexts"]) == canonical_bytes([asdict(s) for s in product.selections]), "actual stored source selections differ"
                    assert source_meta["annotation_product"]["dependency_digest"] == annotation_digest
                report_index = {(r["context"], r["family"], r.get("variant", "default")): r for r in reports}
                append(out / "source-reconstruction.jsonl", dict(source_view_id=source_id, task=dict(row) if row is not None else None,
                    request_standing="actual retained source/annotations; contextual requests proposed, not model consumed" if row is None else "actual candidate source preparation verified",
                    annotation_input_hash=annotation_result["input_hash"],
                    annotation_dependency=annotation_digest,
                    annotations=[a.dependency_digest for a in product.annotations], annotation_errors=annotation_errors,
                    exclusions=product.exclusions, regions=[asdict(r) for r in product.regions],
                    selections=len(product.selections), actual_report_metadata=reports,
                    actual_source_metadata=source_meta,
                    packs={family: [dict(variant=v, anchor=a, fingerprint=p.fingerprint,
                        declaration=json.loads(p.declaration_json)) for v, a, p in variants] for family, variants in packs.items()}))
                correspondence = original_to_actual(reference)
                for index, selection in enumerate(product.selections):
                    try:
                        context = selection.context(product.source, max_chars=cfg.max_context_chars,
                            max_pieces=cfg.max_context_pieces, related=product.related, preparation=product.preparation)
                    except Exception as error:
                        append(out / "context-refusals.jsonl", dict(source_view_id=source_id, index=index,
                            selection=asdict(selection), error=type(error).__name__, reason=str(error)))
                        continue
                    append(out / "source-contexts.jsonl", dict(source_view_id=source_id, index=index,
                        context_id=context.dependency_digest, text=context.text, text_sha256=sha256(context.text.encode()).hexdigest(),
                        intervals=[asdict(interval) for interval in context.intervals], selection=asdict(selection)))
                    if diagnostic_ids:
                        inspect_widened_routes(out, diagnostic_ids, reference["authored"]["records"], selection, view,
                            context, packs, correspondence, prepared, wrapper, cfg, fixed, reference)
                    for family in selection.families:
                        for variant, anchor_role, pack in packs[family]:
                            request = f"{source_id}:{index}:{family}:{variant}"
                            audit = dict(request=request, source_view_id=source_id, index=index, family=family,
                                variant=variant, anchor_role=anchor_role, context_id=context.dependency_digest,
                                pack_fingerprint=pack.fingerprint, request_standing="source-only proposed input" if row is None else "actual source preparation",
                                relevant=[], outside_population=[], errors=[], mapped=[], status="pending")
                            actual = report_index.get((index, family, variant))
                            if actual is None and row is not None:
                                audit["errors"].append({"reason": "no actual native report metadata for this reconstructed request"})
                            elif actual is not None:
                                suffix = actual["preparation"]["synthetic_suffix"]
                                assert suffix in ("", ".")
                                checks = dict(context=actual["context_id"] == actual["context_digest"] == context.dependency_digest,
                                    pack=actual["pack"] == pack.fingerprint,
                                    consumed=sha256((context.text + suffix).encode()).hexdigest() == actual["preparation"]["consumed_text_sha256"])
                                effective_json = source_meta["effective_profiles"].get(actual["effective_profile_ref"])
                                effective = json.loads(effective_json) if effective_json is not None else {}
                                checks["effective_profile"] = (effective.get("profile") == cfg.profile().fingerprint
                                    and effective.get("splitter") == "UnicodeCodepointSplitter"
                                    and effective.get("device") == "cpu" and effective.get("dtype") == "float32"
                                    and effective.get("attention_backend") == "standard"
                                    and effective.get("threads") == cfg.threads
                                    and effective.get("interop_threads") == 1
                                    and effective_json is not None
                                    and sha256(effective_json.encode()).hexdigest() == actual["effective_profile_ref"])
                                audit["actual_context_checks"] = checks
                                if not all(checks.values()):
                                    audit["errors"].append({"reason": "actual preparation metadata differs from reconstruction"})
                            audit["scope_errors"] = scope_errors(context, reference)
                            audit["errors"].extend(audit["scope_errors"])
                            declaration = json.loads(pack.declaration_json)
                            preparation_payload = dict(format=wrapper.FORMAT, sample_id=request, family=family, source=source_id,
                                released_schema=declaration, released_schema_digest=fixed.digest(declaration),
                                target_records=[], target_records_digest=fixed.digest([]))
                            try:
                                # No gold supplied and build_targets=False: this is not a
                                # negative example. Prepare even excluded requests so an
                                # unencoded primary cannot hide a conditioning conflict.
                                native_prepared = wrapper.collate_fn_inference([(context.text, preparation_payload)],
                                    architecture="boundary", max_len=cfg.max_words, build_targets=False,
                                    max_gold_per_query=max_gold, on_capacity_exceeded="raise", error_policy="raise")
                                assert native_prepared.targets is None
                                assert native_prepared.original_lengths[0] <= cfg.max_subwords, "schema-conditioned subword bound exceeded"
                                audit.update(conditioning_digest=full_conditioning_digest(wrapper.last_receipt),
                                    encoding_digest=wrapper.last_receipt["conditioning_digest"],
                                    source_words=wrapper.last_receipt["source_word_counts"][0],
                                    prefix_words=wrapper.last_receipt["samples"][0]["prefix_length"],
                                    total_subwords=native_prepared.original_lengths[0])
                                audit["old_facade_admissible"] = audit["source_words"] <= 512 and audit["total_subwords"] <= 2048
                                append(out / "native-preparation.jsonl", dict(request=request, preparation_only=True,
                                    supervised_targets=False, full_conditioning_digest=audit["conditioning_digest"], **wrapper.last_receipt))
                                all_conditioning_audits[audit["conditioning_digest"]].append(audit)
                            except Exception as error:
                                audit["errors"].append(dict(reason=str(error), type=type(error).__name__,
                                    stage="gold-independent native preparation", traceback=traceback.format_exc()))
                            targets, origins, anchors_seen = [], [], defaultdict(list)
                            family_records = [r for r in reference["authored"]["records"] if r["family"] == family]
                            for record in family_records:
                                identity = record["record_id"]
                                relevant_anchors = literal_anchors(record, "formula" if family == "formula_context" else anchor_role)
                                if family == "formula_context" and args.population_mode == "full-visible" and anchor_role != "formula":
                                    relevant_anchors += literal_anchors(record, anchor_role)
                                if not overlaps(context, relevant_anchors, correspondence):
                                    continue
                                audit["relevant"].append(identity)
                                try:
                                    if family == "formula_context":
                                        applicable, reason = formula_population(record, selection, view, context, correspondence,
                                            prepared, wrapper.native, variant, args.population_mode)
                                        if not applicable:
                                            audit["outside_population"].append({"record_id": identity, "reason": reason})
                                            ledger[identity]["outside_population"].append({"request": request, "reason": reason})
                                            continue
                                    target, mappings, errors = map_record(record, context, pack, correspondence, prepared, wrapper.native)
                                    anchor = target.get(anchor_role)
                                    if not anchor or "start" not in anchor:
                                        errors.append({"role": anchor_role, "reason": "natural instance needs exact present anchor despite optional field cardinality"})
                                    append(out / "mapping-attempts.jsonl", dict(request=request, record_id=identity,
                                        target=target, mappings=mappings, errors=errors))
                                    if errors:
                                        raise ValueError(json.dumps(errors, ensure_ascii=False))
                                    custody = structural_custody(record, selection, view, context, target, args.population_mode)
                                    anchors_seen[(anchor["start"], anchor["end"])].append(identity)
                                    targets.append(target)
                                    origins.append(dict(record_id=identity, mappings=mappings, structural_custody=custody,
                                        native_structural_gold=[f for f in record["fields"] if f["kind"] not in {"literal", "classified"}]))
                                    audit["mapped"].append(identity)
                                    ledger[identity]["mapped_requests"].append(request)
                                except Exception as error:
                                    reason = {"record_id": identity, "type": type(error).__name__, "reason": str(error)}
                                    audit["errors"].append(reason)
                                    ledger[identity]["excluded_requests"].append({"request": request, **reason})
                            collisions = [ids for ids in anchors_seen.values() if len(ids) > 1]
                            if collisions:
                                audit["errors"].append({"reason": "natural-anchor collision", "record_groups": collisions})
                            # A zero is admitted only from the independently empty unit.
                            if not targets and reference["authored"]["records"]:
                                audit["errors"].append({"reason": "no genuine whole-unit-zero premise; nonempty unit empty request remains excluded"})
                            if audit["errors"]:
                                audit["status"] = "excluded"
                            else:
                                payload = dict(format=wrapper.FORMAT, sample_id=request, family=family, source=source_id,
                                    released_schema=declaration, released_schema_digest=fixed.digest(declaration),
                                    target_records=targets, target_records_digest=fixed.digest(targets))
                                try:
                                    batch = wrapper.collate_fn_train([(context.text, payload)], architecture="boundary",
                                        max_len=cfg.max_words, max_gold_per_query=max_gold,
                                        on_capacity_exceeded="raise", error_policy="raise", ignore_missing_entities=False)
                                    receipt = wrapper.last_receipt
                                    consumed = context.text + ("" if context.text.endswith((".", "!", "?")) else ".")
                                    assert batch.original_texts == [consumed]
                                    assert batch.original_lengths[0] <= cfg.max_subwords, "schema-conditioned subword bound exceeded"
                                    assert receipt["exact_conditioning"] and receipt["native_cap_inactive"]
                                    assert full_conditioning_digest(receipt) == audit["conditioning_digest"]
                                    assert receipt["conditioning_digest"] == audit["encoding_digest"]
                                    assert receipt["samples"][0]["expected_records"] == len(targets)
                                    if targets:
                                        assert all(record.field_for_query(next(f.query_id for f in batch.record_specs[0][0].fields if f.name == anchor_role)).values
                                                   for record in batch.targets.records[0])
                                    audit.update(status="collated", source_words=receipt["source_word_counts"][0],
                                        total_subwords=batch.original_lengths[0], conditioning_digest=full_conditioning_digest(receipt),
                                        expected_records=len(targets), genuine_zero=not targets)
                                    audit["native_targets_digest"] = digest(receipt["samples"][0]["native_records"])
                                    receipt_path = out / "native-collation.jsonl"
                                    append(receipt_path, {"request": request, "full_conditioning_digest": audit["conditioning_digest"], **receipt})
                                    proposals.append(dict(audit=audit, input=context.text, output=payload, origins=origins,
                                        semantic_target_digest=digest(sorted(json.dumps(t, ensure_ascii=False, sort_keys=True) for t in targets))))
                                except Exception as error:
                                    audit["status"] = "excluded"
                                    audit["errors"].append({"reason": str(error), "type": type(error).__name__, "traceback": traceback.format_exc()})
                            append(out / "request-audit.jsonl", audit)
                            request_counts[audit["status"]] += 1
                            if audit["status"] == "excluded":
                                for identity in audit["mapped"]:
                                    ledger[identity]["excluded_requests"].append(dict(request=request,
                                        reason="whole context/variant excluded", causes=audit["errors"]))
        conditioning_groups = defaultdict(list)
        for proposal in proposals:
            conditioning_groups[proposal["audit"]["conditioning_digest"]].append(proposal)
        emitted, conflicts, duplicate = 0, 0, 0
        for conditioning_id, proposals_for_conditioning in conditioning_groups.items():
            excluded_same_input = [audit for audit in all_conditioning_audits[conditioning_id] if audit["errors"]]
            if excluded_same_input or len({p["semantic_target_digest"] for p in proposals_for_conditioning}) != 1:
                conflicts += len(proposals_for_conditioning)
                for proposal in proposals_for_conditioning:
                    append(out / "example-disposition.jsonl", dict(request=proposal["audit"]["request"],
                        outcome="excluded", reason="conditioning conflict or incompletely labelled identical input"))
                    append(out / "conditioning-conflicts.jsonl", dict(request=proposal["audit"]["request"],
                        conditioning_digest=proposal["audit"]["conditioning_digest"],
                        target_digest=proposal["semantic_target_digest"], records=proposal["audit"]["mapped"],
                        excluded_same_input_requests=[a["request"] for a in excluded_same_input]))
                    for identity in proposal["audit"]["mapped"]:
                        ledger[identity]["excluded_requests"].append(dict(request=proposal["audit"]["request"],
                            reason="identical model conditioning has different gold target population"))
                continue
            chosen = proposals_for_conditioning[0]
            emitted += 1
            duplicate += len(proposals_for_conditioning) - 1
            aliases = [p["audit"]["request"] for p in proposals_for_conditioning]
            append(out / "training-targets.jsonl", {"input": chosen["input"], "output": chosen["output"]})
            append(out / "training-target-origins.jsonl", dict(request=chosen["audit"]["request"], aliases=aliases,
                origins=chosen["origins"], audit=chosen["audit"],
                all_alias_origins=[dict(request=p["audit"]["request"], origins=p["origins"],
                    source_view_id=p["audit"]["source_view_id"], context_id=p["audit"]["context_id"]) for p in proposals_for_conditioning]))
            for proposal in proposals_for_conditioning:
                append(out / "example-disposition.jsonl", dict(request=proposal["audit"]["request"],
                    outcome="emitted" if proposal is chosen else "deduplicated", emitted_request=chosen["audit"]["request"]))
                for identity in proposal["audit"]["mapped"]:
                    ledger[identity]["emitted_requests"].append(chosen["audit"]["request"])
        for entry in ledger.values():
            entry["emitted_requests"] = sorted(set(entry["emitted_requests"]))
            entry["status"] = "represented" if entry["emitted_requests"] else "excluded"
            if not entry["mapped_requests"] and not entry["excluded_requests"]:
                entry["limitation"] = "no applicable bounded request contains independently anchored full reading"
            elif not entry["emitted_requests"]:
                entry["limitation"] = "context-level completeness, collision, capacity, conditioning or actual-report gate; inspect request audits"
            append(out / "record-disposition.jsonl", entry)
        assert len(ledger) == 270
        # Reload actual on-disk raw dictionaries; the wrapper sees precisely this order.
        reload_count = 0
        original_receipts = {proposal["audit"]["request"]: proposal["audit"] for proposal in proposals}
        if (out / "training-targets.jsonl").exists():
            for line in (out / "training-targets.jsonl").read_text().splitlines():
                payload = json.loads(line)
                wrapper = next(iter(states.values()))
                wrapper.collate_fn_train([(payload["input"], payload["output"])], max_len=4096,
                    max_gold_per_query=64, on_capacity_exceeded="raise", error_policy="raise")
                assert wrapper.last_receipt["exact_conditioning"]
                assert full_conditioning_digest(wrapper.last_receipt) == original_receipts[payload["output"]["sample_id"]]["conditioning_digest"]
                assert wrapper.last_receipt["conditioning_digest"] == original_receipts[payload["output"]["sample_id"]]["encoding_digest"]
                assert digest(wrapper.last_receipt["samples"][0]["native_records"]) == original_receipts[payload["output"]["sample_id"]]["native_targets_digest"]
                append(out / "reload-collation.jsonl", dict(request=payload["output"]["sample_id"],
                    conditioning_digest=wrapper.last_receipt["conditioning_digest"],
                    full_conditioning_digest=full_conditioning_digest(wrapper.last_receipt),
                    targets_digest=digest(wrapper.last_receipt["samples"][0]["native_records"])))
                reload_count += 1
        summary = dict(outcome="passed", denominator=DENOMINATOR, original_records=len(ledger),
            represented=dict(Counter(e["family"] for e in ledger.values() if e["emitted_requests"])),
            excluded=dict(Counter(e["family"] for e in ledger.values() if not e["emitted_requests"])),
            represented_with_assembly_exclusion=[e["record_id"] for e in ledger.values() if e["emitted_requests"] and e["assembly_exclusions"]],
            examples=emitted, reload_examples=reload_count, duplicate_conditionings=duplicate,
            conflicting_requests=conflicts, population=population,
            requests=dict(request_counts),
            model_loaded=False, forward=False, training=False, heldout=False, database_mutation=False)
        assert emitted == reload_count
        assert source_receipts == [file_receipt(source_root / p) for p in source_modules], "trusted source changed during reconstruction"
        assert configuration["registry"] == file_receipt(registry_path), "contextual registry changed during reconstruction"
        frozen_processor = out / "fixed_schema_processor-executed.py.txt"
        assert frozen_processor.read_bytes() == PROCESSOR.read_bytes(), "settled processor changed during reconstruction"
        write(out / "summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False), flush=True)
    except BaseException as error:
        write(out / "failure.json", {"outcome": "failed", "type": type(error).__name__, "reason": str(error), "traceback": traceback.format_exc()})
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--attempt", default="attempt-001")
    parser.add_argument("--population-mode", choices=("selected-primary", "full-visible"), default="selected-primary")
    parser.add_argument("--routing-diagnostic", action="store_true")
    parser.add_argument("--completed-run-authorized", required=True, action="store_true")
    args = parser.parse_args()
    if Path(args.attempt).name != args.attempt or not args.attempt.startswith("attempt-"):
        parser.error("attempt must be one new local attempt-* folder name")
    main(args)
