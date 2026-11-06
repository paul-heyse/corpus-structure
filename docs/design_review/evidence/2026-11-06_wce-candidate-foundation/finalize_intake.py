"""Finalize already successful source-ready intake without repeating conversion."""

import json
from pathlib import Path

from sqlalchemy import text

from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.operations import seal_cut
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_sources import StructuralPassageSelection, prepare_structural_sources
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "intake003"
receipt = json.loads((OUTPUT / "run.json").read_bytes())
if receipt["status"] != "source_ready" or receipt["run_id"] != 105:
    raise ValueError("finalization requires exact retained successful source-ready run105")
settings = Settings()
with open_runtime_engine(settings, "wce-source-finalize", purpose="write") as engine:
    with engine.begin() as conn:
        cut = seal_cut(conn, receipt["run_id"], "wce-normal-source-final", final=True)
    consolidate_cut(engine, cut, "wce-normal-source-result:105")
with open_runtime_engine(settings, "wce-source-freeze", purpose="read") as engine:
    with engine.connect() as conn:
        rows = tuple(dict(row) for row in conn.execute(text("SELECT v.id, length(v.projection->>'text') AS chars FROM kb.source_view v JOIN ops.run_source_view m ON m.source_view_id=v.id WHERE m.run_id=:run ORDER BY v.id"), {"run": receipt["run_id"]}).mappings())
    selected = tuple(StructuralPassageSelection(run_id=receipt["run_id"], source_view_id=row["id"], passage_id=f"normal-source-{row['id']}", start=0, end=row["chars"], scope="wce-statistics-normal-002") for row in rows if row["chars"] > 100)
    frozen = prepare_structural_sources(engine, selected)
packet = {"protocol": "wce-authenticated-normal-source-1", "sources": [s.model_dump(mode="json", exclude_none=True) for s in frozen.sources], "passages": [p.model_dump(mode="json", exclude_none=True) for p in frozen.passages], "source_cut": json.loads((HERE / "normal-excerpt002/source-cut-001.json").read_bytes()), "native_partition_assignment": "unchanged; original Grinstead source-group authority applies", "use": "exposed source-family development refinement, not new heldout origin", "producer_executed": False, "source_intake_run": receipt["run_id"], "source_intake_cut": cut}
with (OUTPUT / "source-packet-002.json").open("x") as stream:
    json.dump(packet, stream, ensure_ascii=False, indent=2)
    stream.write("\n")
with (OUTPUT / "finalize-result.json").open("x") as stream:
    json.dump({"outcome": "passed", "run_id": receipt["run_id"], "cut_id": cut, "sources": len(frozen.sources), "provider_rerun": False, "earlier_driver_failure": "expected finished instead of normal source_ready status; source production had succeeded"}, stream, indent=2)
    stream.write("\n")
print(json.dumps({"outcome": "passed", "run_id": receipt["run_id"], "cut_id": cut, "sources": len(frozen.sources)}))
