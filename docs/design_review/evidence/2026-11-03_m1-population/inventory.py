"""Freeze detached M1 development sources using existing read-only selected-view readers.

No predictions, task claims, evaluator answers, providers or publication calls are read/run.
Run from the repository root with the explicitly selected source database settings.
"""

from __future__ import annotations

import gzip
import json
import random
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from sqlalchemy import select, text

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_views import load_source_view, selected_source_views
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
BASELINE = "ae30daba41aec5b4b89fc2ce6a7a4872f46f1f56"
SEED = 20261103
SELECTION = HERE.parent / "2026-11-01_pdf-current-consumers/selection-run6-20261103-00002.json"


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def main():
    paths = [HERE / name for name in ("sources.json.gz", "regions.jsonl", "sample.json", "manifest.json")]
    if any(path.exists() for path in paths):
        raise FileExistsError("Frozen inventory exists; choose a new evidence revision")
    selection_raw = SELECTION.read_bytes()
    selection = json.loads(selection_raw)
    expected = {view["id"]: view for view in selection["analysis_views"]}
    views, documents, sources = [], {}, []
    with open_runtime_engine(Settings(), "ci-m1-source-inventory", purpose="read") as engine:
        with engine.connect() as conn:
            conn.execute(text("SET TRANSACTION READ ONLY"))
            transaction_read_only = conn.execute(text("SHOW transaction_read_only")).scalar_one()
            run_table = table("ops.run")
            run = conn.execute(select(run_table).where(run_table.c.id == 6)).mappings().one()
            references = selected_source_views(conn, 6)
            selected_ids = {ref.id for ref in references if ref.analysis_eligible}
            if selected_ids != set(expected):
                raise ValueError("Analysis selection differs from frozen run6 lead")
            for ref in references:
                if not ref.analysis_eligible:
                    continue
                pin = asdict(ref)
                if pin != expected[ref.id]:
                    raise ValueError("Source view pin changed")
                view = load_source_view(conn, ref.id, analysis=False)
                document_table = table("kb.document")
                document = conn.execute(select(document_table).where(document_table.c.id == ref.document_id)).mappings().one()
                documents[ref.document_id] = {key: document[key] for key in ("id", "project_id", "key", "source_uri", "content_hash", "original_path", "mime", "title")}
                title = next(item.get("name") for item in view.items if item["self_ref"] == ref.section_pointer)
                source = dict(pin=pin, title=title, text=view.text, pieces=view.pieces, items=view.items, ancestors=view.ancestors, health=view.health)
                sources.append(source)
                views.append(dict(pin=pin, title=title, text_characters=len(view.text), pieces=len(view.pieces), items=len(view.items), item_labels=dict(Counter(item.get("label", "group") for item in view.items)), source_sha256=sha256(encoded(source)).hexdigest(), health=view.health))
            run_pin = {key: run[key] for key in ("id", "project_id", "release_id")}
    regions = []
    for source in sources:
        source_digest = sha256(encoded(source)).hexdigest()
        native = {item["self_ref"]: item for item in source["items"]}
        for index, piece in enumerate(source["pieces"]):
            item = native.get(piece.get("item_ref"), {})
            start, end = piece["start"], piece["end"]
            quote = source["text"][start:end]
            regions.append(dict(id=f"view{source['pin']['id']}:piece{index}", source_view_id=source["pin"]["id"], source_sha256=source_digest, origin_group=f"pdf:{documents[source['pin']['document_id']]['content_hash']}", piece=piece, label=item.get("label", "unknown"), native_pointer=piece.get("item_ref"), text=quote, text_sha256=sha256(quote.encode()).hexdigest()))
    sample_count = min(40, len(regions))
    sample = random.Random(SEED).sample(regions, sample_count)
    challenge = []
    for label in sorted({row["label"] for row in regions}):
        candidates = [row for row in regions if row["label"] == label]
        challenge.extend(candidates[:2])
    payloads = [gzip.compress(encoded(sources), mtime=0), b"".join(encoded(row) + b"\n" for row in regions), encoded(dict(seed=SEED, sampling_unit="projection piece including empty pieces", population_size=len(regions), sample_size=sample_count, inclusion_probability=sample_count / len(regions), method="Python random.Random(seed).sample over view-order/piece-order universe", random_region_ids=[row["id"] for row in sample], challenge_method="first two pieces per native item label; purposive, no prevalence estimate", challenge_region_ids=[row["id"] for row in challenge], partition="development", independent_origin_groups=1))]
    manifest = dict(created_at=datetime.now(UTC).isoformat(), baseline=BASELINE, claim="Tested read-only source freezing; guideline/release sampling remain Proposed", run=run_pin, transaction_read_only=transaction_read_only, selection=dict(path=str(SELECTION.relative_to(HERE.parents[3])), sha256=sha256(selection_raw).hexdigest()), documents=list(documents.values()), views=views, source_origin_groups=len(documents), total_regions=len(regions), eligible_record_count="unknown until independent source authoring", original_page_audit="not_run; no original-page denominator", family_gate="unestablished", reference_authoring="not_run", production_inference="not_run", artifacts={path.name: dict(sha256=sha256(payload).hexdigest(), bytes=len(payload)) for path, payload in zip(paths, payloads, strict=False)})
    payloads.append(encoded(manifest))
    for path, payload in zip(paths, payloads, strict=True):
        with path.open("xb") as stream:
            stream.write(payload)
    print(json.dumps(dict(outcome="passed", transaction_read_only=transaction_read_only, source_views=len(views), source_origin_groups=len(documents), regions=len(regions), sample=sample_count, labels=dict(Counter(row["label"] for row in regions))), sort_keys=True))


if __name__ == "__main__":
    main()
