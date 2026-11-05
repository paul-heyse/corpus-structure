"""Read-only PCE02 replay of task37, using archived producer configuration and source.

No reference labels, model initialization, producer execution or database writes.
Outputs use exclusive creation; the coordinator owns this evidence folder's account.
"""
from collections import Counter
from dataclasses import asdict
from pathlib import Path
import json
from hashlib import sha256
from types import SimpleNamespace

from sqlalchemy import select
from corpus_structure.methods.contribution_adapter import replay_retained_contributions
from corpus_structure.methods.m1_source import configured_pack_variants
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent


def main():
    tasks, configs, runs = map(table, ("ops.task", "ops.method_config", "ops.run"))
    with open_runtime_engine(Settings(), "pce02-task37-replay", purpose="read") as engine, read_snapshot(engine) as conn:
        row = conn.execute(select(tasks.c.unit_id, configs.c.params, runs.c.release_id)
            .join(configs, configs.c.id == tasks.c.method_config_id)
            .join(runs, runs.c.id == tasks.c.run_id)
            .where(tasks.c.id == 37, tasks.c.run_id == 14)).mappings().one()
        prepared = open_release(conn, row["release_id"])
        reader = BoundReader(conn, 14, prepared, analysis=False,
            read_budget=PublishedReadBudget(40_000, 256 * 1024**2))
        view = reader.source_view(row["unit_id"])
        upstream = reader.source_result(view.ref.id, "extract.m1_candidates")
        assert upstream is not None
        config = SimpleNamespace(**row["params"])
        variants = configured_pack_variants(prepared, config)
        packs = {pack.fingerprint: asdict(pack) for items in variants.values() for _, _, pack in items}
        batch = replay_retained_contributions(reader, view, upstream, schema_packs=packs,
            context_bounds=dict(max_chars=config.max_context_chars, max_pieces=config.max_context_pieces, max_sources=16))
        source = dict(run_id=14, task_id=37, source_view_id=view.ref.id, release_id=row["release_id"],
            upstream_sha256=sha256(canonical_bytes(upstream)).hexdigest(),
            configuration=row["params"], schema_packs=packs,
            reports=len(upstream["parse_detail"]["reports"]),
            table_candidates=sum(record["family"] == "table" for record in upstream["records"]))
        result = dict(source=source, operations=batch.operations, contributions=batch.contributions,
            coordinate_texts=batch.coordinate_texts,
            scope="retained task37 raw reports, no provider or local assessment claim")
        destination = HERE / "raw" / "pce02-task37-replay-001.json"
        with destination.open("xb") as out:
            out.write(canonical_bytes(result) + b"\n")
        summary = dict(outcome="passed", output=str(destination),
            operations=len(batch.operations), contributions=len(batch.contributions),
            outcomes=dict(Counter(op["outcome"] for op in batch.operations)),
            kinds=dict(Counter(row["kind"] for row in batch.contributions)),
            unavailable=dict(Counter(op.get("reason", "") for op in batch.operations if op["outcome"] == "unsupported")),
            report_count=source["reports"], table_candidates=source["table_candidates"])
        with (HERE / "raw" / "pce02-task37-replay-summary-001.json").open("x") as out:
            json.dump(summary, out, indent=2)
        print(json.dumps(summary))

if __name__ == "__main__":
    main()
