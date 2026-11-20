"""Read bounded typed counts and retained native phases for the settled contrast."""

import json
import re
from pathlib import Path

from corpus_structure.semantic.metadata import table
from sqlalchemy import Text, cast, create_engine, func, select

ROOT = Path("/home/paul/corpus-structure")
FOLDER = Path(__file__).resolve().parent
RAW = FOLDER / "raw"
result = json.loads(
    (ROOT / "build/udm20-regional/failed-records-contrast-run.json").read_text()
)
snapshot = result["native"]["snapshot"]
obligations = {row["obligation_id"]: row for row in snapshot["obligations"]}
sentence_uses = [
    use
    for use in snapshot["uses"]
    if obligations[use["obligation_id"]]["operation_id"]
    == "segment.sentences/source-native"
]
products = [
    product["product_id"] for use in sentence_uses for product in use["products"]
]
intents = [obligations[use["obligation_id"]]["intent_id"] for use in sentence_uses]
members = table("kb.data_product_member")
kinds = table("sem.data_kind_contract")
intent = table("ops.data_completion_intent")
engine = create_engine(
    "postgresql+psycopg://paul@/corpus_structure_ddo_stage?host=/var/run/postgresql&port=5434"
)
try:
    with engine.connect() as connection:
        counts = [
            dict(row)
            for row in connection.execute(
                select(kinds.c.kind, func.count().label("members"))
                .select_from(
                    members.join(
                        kinds, members.c.kind_contract == kinds.c.kind_contract
                    )
                )
                .where(members.c.product_id.in_(products))
                .group_by(kinds.c.kind)
                .order_by(kinds.c.kind)
            ).mappings()
        ]
        sizes = [
            dict(row)
            for row in connection.execute(
                select(
                    intent.c.id,
                    intent.c.producer_task_id,
                    func.octet_length(cast(intent.c.payload, Text)).label(
                        "jsonb_text_bytes"
                    ),
                )
                .where(intent.c.id.in_(intents))
                .order_by(intent.c.id)
            ).mappings()
        ]
finally:
    engine.dispose()
fates = {
    "outcome": "passed",
    "cleanup": "established",
    "demand_id": snapshot["demand_id"],
    "obligations": [
        {
            "operation": row["operation_id"],
            "fate": row["fate"],
            "id": row["obligation_id"],
        }
        for row in snapshot["obligations"]
    ],
}
assert len(fates["obligations"]) == 5
assert all(row["fate"] == "fulfilled" for row in fates["obligations"])
(RAW / "n36-contrast-fates.json").write_text(json.dumps(fates, indent=2) + "\n")
census = {
    "project": "udm20-regional-failed-records-contrast",
    "scope": "exact two published sentence products in the settled managed result",
    "products": products,
    "counts": counts,
    "intents": sizes,
}
(RAW / "n36-contrast-member-counts.json").write_text(
    json.dumps(census, indent=2) + "\n"
)
pattern = re.compile(
    r"^(?P<at>\d{4}-\d\d-\d\d .*?) \[(?P<pid>\d+)\].*?LOG:  duration: "
    r"(?P<ms>[\d.]+) ms  execute .*?: SELECT CAST\(ops\.(?P<operation>\w+)\(",
    re.MULTILINE,
)
observed = [
    {
        "at": match["at"],
        "pid": int(match["pid"]),
        "milliseconds": float(match["ms"]),
        "operation": match["operation"],
    }
    for match in pattern.finditer(
        (RAW / "failed-records-contrast-postgresql.log").read_text()
    )
    if match["operation"]
    in {
        "retain_data_completion_intent",
        "publish_data_derivation",
        "inspect_data_completion_draft",
    }
]
(RAW / "n36-contrast-sql-phases.json").write_text(json.dumps(observed, indent=2) + "\n")
print(json.dumps({"fates": fates, "census": census, "phases": observed}, indent=2))
