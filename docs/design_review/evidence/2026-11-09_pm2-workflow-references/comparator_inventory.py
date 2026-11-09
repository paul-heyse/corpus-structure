"""Check which retained M1 products cover the exact new workflow anchors."""

import json
from pathlib import Path

from corpus_structure.semantic.contribution_queries import read_source_contributions
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.query import bind_completed_result, read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
SCOPES = {
    "definition_use": ("focal",),
    "definition_target": ("term", "cue", "content"),
    "conditional_frequency": ("inner_premise", "lexical_host"),
}
RUN = 407
CUT = 517


def main():
    packet = json.loads((HERE / "raw/source-windows.json").read_bytes())
    result = {}
    with (
        open_runtime_engine(
            Settings(), "pm2-comparator-anchor-inventory", purpose="read"
        ) as engine,
        read_snapshot(engine) as conn,
    ):
        selected = bind_completed_result(conn, RUN)
        assert selected.completed_cut_id == CUT
        for case, names in SCOPES.items():
            row = packet["cases"][case]
            outputs = {}
            for name in names:
                anchors = row["anchors"][name]["native_anchors"]
                scope = tuple(
                    {k: a[k] for k in ("space", "pointer", "start", "end")} for a in anchors
                )
                inventory = read_source_contributions(
                    conn,
                    prepared=selected.prepared,
                    run_id=RUN,
                    cut_id=CUT,
                    source_view_id=row["m1_corresponding_view"],
                    method="extract.m1_candidates",
                    anchor_scopes=scope,
                    include_details=True,
                    limit=100,
                )
                outputs[name] = {
                    "items": [
                        {k: item.get(k) for k in ("contribution_id", "kind", "semantic_type")}
                        for item in inventory.contributions
                    ],
                    "more": inventory.more,
                }
            result[case] = {"view": row["m1_corresponding_view"], "anchors": outputs}
    print(canonical_bytes({"run": RUN, "cut": CUT, "cases": result}).decode())


if __name__ == "__main__":
    main()
