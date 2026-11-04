"""Read-only reassembly of actual sealed decoder reports; no new model/publication."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

from corpus_structure.methods.gliner import GlinerPreparation, GlinerReport
from corpus_structure.methods.m1_source import FAMILIES, configured_packs
from corpus_structure.methods.record_assembly import (
    LiteralSpan,
    NativeRecordGroup,
    RoleInput,
    assemble_records,
    reconcile_record_candidates,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_contexts import (
    ContextRefused,
    ContextRelationship,
    ContextRetrieval,
    NativeSourceContext,
    NativeSourcePin,
    NativeSpanEvidence,
    PreparedNativeSources,
    RelatedNativeSource,
    RetrievalOutcome,
    SourceSlice,
    SyntheticText,
)
from corpus_structure.settings import Settings
from sqlalchemy import select, text


def pin(raw):
    return NativeSourcePin(**dict(raw, native_product=ProductReference(**raw["native_product"])))


def selection(raw):
    row = dict(raw)
    row["pieces"] = tuple(SourceSlice(**piece) if "source_view_id" in piece else SyntheticText(**piece)
                          for piece in row["pieces"])
    row["retrievals"] = tuple(ContextRetrieval(**dict(retrieval,
        relationship=ContextRelationship(retrieval["relationship"]),
        outcome=RetrievalOutcome(retrieval["outcome"]),
        candidates=tuple(pin(value) for value in retrieval["candidates"]),
        selected=tuple(retrieval["selected"]), excluded=tuple(retrieval["excluded"])))
        for retrieval in row["retrievals"])
    row["relationships"] = tuple((identity, ContextRelationship(relation), reason)
                                 for identity, relation, reason in row["relationships"])
    for name in ("families", "missing_roles", "local_dispositions"):
        row[name] = tuple(tuple(value) if isinstance(value, list) else value for value in row[name])
    return SimpleNamespace(**row)


def structural_group(raw):
    fields = []
    for field in raw["fields"]:
        value = dict(field)
        for name in ("spans", "cues", "inspected_spans"):
            value[name] = tuple(LiteralSpan(**span) for span in value[name])
        value["dependencies"] = tuple(value["dependencies"])
        fields.append(RoleInput(**value))
    return NativeRecordGroup(tuple(fields), raw["reason"], tuple(raw["dependencies"]))


def replay(reader, task, config, result):
    prepared = reader.prepared
    cfg = SimpleNamespace(**config)
    packs = configured_packs(prepared, cfg)
    view = reader.source_view(task["unit_id"])
    envelope = reader.source_result(view.ref.id, "extract.m1_candidates")
    if envelope is None or canonical_bytes(envelope["records"]) != canonical_bytes(result["records"]):
        raise ValueError("sealed task/report binding differs from the named raw result")
    details = envelope["parse_detail"]
    primary = native_source_frame(view, ())
    if canonical_bytes(asdict(NativeSourcePin.from_source(primary))) != canonical_bytes(details["source_pin"]):
        raise ValueError("retained primary source pin differs")
    selections = tuple(selection(raw) for raw in details["contexts"])
    identities = {identity for value in selections for identity, _, _ in value.relationships}
    sources = {primary.source_view_id: primary}
    sources.update({identity: native_source_frame(reader.source_view(identity), ()) for identity in identities})
    preparation = PreparedNativeSources(tuple(sources.values()), max_sources=9)
    assemblies, diagnostics, counts, bound_contexts = [], [], Counter(), []
    for entry in details["reports"]:
        if "report" not in entry:
            continue
        selected = selections[entry["context"]]
        related = tuple(RelatedNativeSource(sources[identity], relationship, reason)
                        for identity, relationship, reason in selected.relationships)
        context = NativeSourceContext(primary, related,
            selected.pieces or (SourceSlice(primary.source_view_id, selected.start, selected.end),),
            ",".join(selected.families), details["policy"], selected.reason,
            retrievals=selected.retrievals, max_chars=cfg.max_context_chars,
            max_pieces=cfg.max_context_pieces, version=2, preparation=preparation)
        raw = dict(entry["report"])
        profile_ref = raw.pop("effective_profile_ref")
        profile = details["effective_profiles"][profile_ref]
        if sha256(profile.encode()).hexdigest() != profile_ref:
            raise ValueError("effective profile bytes differ")
        raw["effective_profile_json"] = profile
        prepared_input = dict(raw["preparation"])
        consumed = context.text + prepared_input["synthetic_suffix"]
        if sha256(consumed.encode()).hexdigest() != prepared_input.pop("consumed_text_sha256"):
            raise ValueError("retained consumed-text digest differs; no context fallback")
        raw["preparation"] = GlinerPreparation(**dict(prepared_input, consumed_text=consumed))
        raw["diagnostics"] = tuple(tuple(value) for value in raw["diagnostics"])
        report = GlinerReport(**raw)
        family = entry["family"]
        contract, anchor = FAMILIES[family]
        supplements = {}
        structures = [structural_group(group) for item in details["reports"]
                      if item.get("operation") == "native_structure" and item["family"] == family
                      and item["context"] == entry["context"] for group in item["groups"]]
        for index, group in enumerate(report.raw.get(family, ())):
            if family == "definition":
                supplements[index] = NativeRecordGroup((RoleInput("scope", native_pointer=view.ref.section_pointer),),
                    "selected native section is the explicit definition scope")
            elif family == "formula_context" and structures:
                supplements[index] = structures[0]
            elif family == "table":
                raw_value = group.get("cell_value")
                if isinstance(raw_value, dict):
                    try:
                        evidence = context.map_span(raw_value["start"], raw_value["end"],
                            literal=raw_value["text"], allow_multiple=True)
                    except (KeyError, TypeError, ContextRefused):
                        continue  # exact original association refusal; no fabricated cell
                    if any(not isinstance(piece, NativeSpanEvidence) for piece in evidence):
                        raise ValueError("retained table association is not canonical native evidence")
                    cells = {piece.cell_index for piece in evidence}
                    if len(cells) == 1 and None not in cells:
                        pointer = f"{selected.region}/data/table_cells/{next(iter(cells))}"
                        matching = [candidate for candidate in structures
                                    if any(field.role == "cell" and field.native_pointer == pointer
                                           for field in candidate.fields)]
                        if len(matching) == 1:
                            supplements[index] = matching[0]
        assembled = assemble_records(prepared, context, packs[family], report, contract=contract,
            anchor_role=anchor, policy_version=cfg.record_policy_version,
            occurrence_policy=cfg.occurrence_policy, supplements=supplements)
        assemblies.append(assembled)
        diagnostics.extend(dict(asdict(item), family=family, context=entry["context"])
                           for item in assembled.diagnostics)
        counts[family] += len(assembled.records)
        bound_contexts.append(dict(context_index=entry["context"], family=family,
            context_digest=context.dependency_digest, pack_fingerprint=packs[family].fingerprint,
            raw_group_count=len(report.raw.get(family, ())), consumed_text_sha256=sha256(consumed.encode()).hexdigest()))
    unique = reconcile_record_candidates(prepared, tuple(assemblies))
    rows = [row.model_dump(mode="json") for row in unique]
    branch_counts = Counter(dependency for row in rows for dependency in row["computation_dependencies"]
                           if dependency.startswith("source-reading-branch:"))
    return dict(standing="read_only_reassembly; not a new model run or publication",
                original_record_count=len(result["records"]), reassembled_records=[row.model_dump(mode="json") for row in unique],
                emitted_by_family=dict(counts), retained_by_family=dict(Counter(row["family"] for row in rows)),
                retained_branch_counts=dict(branch_counts), bound_reports=bound_contexts,
                binding_check="every retained decoder report reassembled under exact context/consumed-text/pack binding; no fallback",
                replay_inputs=dict(task_configuration=config, original_envelope=result,
                    source_frames=[asdict(source) for source in sources.values()],
                    packs={family: asdict(pack) for family, pack in packs.items()}),
                diagnostics=diagnostics,
                diagnostic_counts=dict(Counter(row["code"] for row in diagnostics)),
                quality_claim="not_established")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("run", "cut", "task"):
        parser.add_argument("--" + name, type=int, required=True)
    parser.add_argument("--release", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    with open_runtime_engine(Settings(), "m1-stored-group-replay", purpose="read") as engine, engine.connect() as conn:
        conn.execute(text("SET TRANSACTION READ ONLY"))
        tasks, results, cuts, configs, methods = map(table, ("ops.task", "ops.task_result", "ops.cut_task", "ops.method_config", "ops.method"))
        row = conn.execute(select(tasks, results.c.body, configs.c.params, methods.c.name).select_from(
            tasks.join(results, results.c.task_id == tasks.c.id).join(cuts, cuts.c.task_id == tasks.c.id)
            .join(configs, configs.c.id == tasks.c.method_config_id).join(methods, methods.c.id == configs.c.method_id)
        ).where(tasks.c.id == args.task, tasks.c.run_id == args.run, tasks.c.release_id == args.release,
                cuts.c.cut_id == args.cut, cuts.c.origin_task_id == tasks.c.id,
                methods.c.name == "extract.m1_candidates")).mappings().one()
        prepared = open_release(conn, args.release)
        value = replay(BoundReader(conn, args.run, prepared, cut_id=args.cut, analysis=False),
                       row, row["params"], row["body"])
        value.update(run_id=args.run, task_id=args.task, cut_id=args.cut, release_id=args.release,
                     original_report_sha256=sha256(canonical_bytes(row["body"])).hexdigest())
        from corpus_structure.methods import record_assembly
        assembly_bytes = Path(record_assembly.__file__).read_bytes()
        (args.out / "executed-record-assembly.py").write_bytes(assembly_bytes)
        value["reassembly_source_sha256"] = sha256(assembly_bytes).hexdigest()
        inputs = canonical_bytes(value.pop("replay_inputs"))
        (args.out / "replay-inputs.json").write_bytes(inputs)
        value["replay_inputs_sha256"] = sha256(inputs).hexdigest()
        (args.out / "replay.json").write_bytes(canonical_bytes(value))
    print(json.dumps({key: value[key] for key in ("standing", "original_record_count", "retained_by_family", "retained_branch_counts", "diagnostic_counts")}))


if __name__ == "__main__":
    main()
