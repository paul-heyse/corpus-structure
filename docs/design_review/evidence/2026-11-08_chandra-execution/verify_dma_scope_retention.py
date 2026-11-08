"""Read the stopped scope pins through the restricted development Reader."""

import json
from pathlib import Path

from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings


def main() -> None:
    manifest = Path(__file__).parent / "raw/book-shadow-377/dma-stopped-scope-pins.json"
    groups = json.loads(manifest.read_text())["groups"]
    members = [member for group in groups for member in group["members"]]
    if len(groups) != 17 or len(members) != 68:
        raise ValueError("stopped scope inventory differs from its recorded bound")
    pins = [
        {**member[kind], "mapped": kind == "mapped"}
        for member in members
        for kind in ("raw", "mapped")
    ]
    if len({(pin["task_id"], pin["product_key"]) for pin in pins}) != 136:
        raise ValueError("stopped scope pins are not unique")
    with (
        open_runtime_engine(
            Settings(), "dma-shadow-retention", purpose="read"
        ) as engine,
        engine.connect() as conn,
    ):
        if conn.exec_driver_sql("select current_database(),current_user").one() != (
            "corpus_structure_dev",
            "corpus_sem_reader",
        ):
            raise ValueError(
                "stopped scope verification requires the development Reader"
            )
        observed = conn.exec_driver_sql(
            """select count(*), count(i.task_id)
            from jsonb_to_recordset(%s::jsonb) q(
                run_id bigint,task_id bigint,product_key text,content_digest text,mapped boolean
            )
            join ops.pdf_product p using(task_id,product_key,content_digest)
            join ops.task t on t.id=p.task_id and t.run_id=q.run_id
            join ops.run r on r.id=t.run_id and r.project_id='nce-grinstead-snell-full-book'
            left join ops.pdf_visual_index i
              on q.mapped and i.task_id=p.task_id and i.product_key=p.product_key
            where p.kind='recognition_observation' and (not q.mapped or i.task_id is not null)""",
            (json.dumps(pins),),
        ).one()
    if observed != (136, 68):
        raise ValueError(f"stopped scope custody is incomplete: {observed}")
    print(
        json.dumps(
            {
                "outcome": "passed",
                "groups": 17,
                "scopes": 68,
                "pins": 136,
                "mapped_locators": 68,
            }
        )
    )


if __name__ == "__main__":
    main()
