"""Read retained task110 and compare three schemas on two exact retained inputs.

No corpus products, references, evaluations or model parameters are written. The
source-only read uses existing native custody and never reads authored labels.
"""

import json
import re
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from corpus_structure.methods.gliner import GlinerInput, GlinerPack
from corpus_structure.methods.gliner_worker import GlinerWorker
from corpus_structure.methods.m1_source import M1Config
from corpus_structure.settings import Settings

ROOT = Path(__file__).parent


def main():
    engine = create_engine(make_url(Settings().database.sqlalchemy_url).set(username="paul"))
    try:
        with engine.connect() as conn, conn.begin():
            conn.exec_driver_sql("SET TRANSACTION READ ONLY")

            def field(name):
                return conn.scalar(
                    text(
                        "SELECT data.record_source_json("
                        "data.report_field(body->'parse_detail',:name)) "
                        "FROM ops.task_result WHERE task_id=110"
                    ),
                    dict(name=name),
                )

            contexts, reports = field("contexts"), field("local_reports")
            regions, selection = field("regions"), field("source_region_selection")
            packs, statuses = field("schema_packs"), field("local_execution")
            release = conn.scalar(text("SELECT release_id FROM ops.task WHERE id=110"))
            config = conn.scalar(
                text(
                    "SELECT params FROM ops.task t JOIN ops.method_config c "
                    "ON c.id=t.method_config_id "
                    "WHERE t.id=110"
                )
            )
            view_ids = {
                piece["source_view_id"]
                for context in contexts
                for piece in context["pieces"]
                if "source_view_id" in piece
            }
            views = {
                identity: conn.scalar(
                    text("SELECT projection->>'text' FROM kb.source_view WHERE id=:identity"),
                    dict(identity=identity),
                )
                for identity in view_ids
            }

        reconstructed = {}
        summaries = []
        entity_totals, relation_totals, attribute_totals = Counter(), Counter(), Counter()
        for report in reports:
            index, raw = report["context"], json.loads(report["report"]["raw_json"])
            context = contexts[index]
            source = "".join(
                piece["text"]
                if "text" in piece
                else views[piece["source_view_id"]][piece["start"] : piece["end"]]
                for piece in context["pieces"]
            )
            reconstructed[index] = source
            preparation = report["report"]["preparation"]
            actual_hash = sha256((source + preparation["synthetic_suffix"]).encode()).hexdigest()
            assert actual_hash == preparation["consumed_text_sha256"]
            assert len(source.encode()) == preparation["input_bytes"]
            entity_counts = {key: len(value) for key, value in raw.get("entities", {}).items()}
            relation_counts = {
                key: len(value) for key, value in raw.get("relation_extraction", {}).items()
            }
            entity_totals.update(entity_counts)
            relation_totals.update(relation_counts)
            for population in raw.get("entities", {}).values():
                for item in population:
                    attribute_totals.update(set(item) - {"text", "start", "end", "confidence"})
            summaries.append(
                dict(
                    context=index,
                    region=context["region"],
                    input_chars=len(source),
                    input_sha256=sha256(source.encode()).hexdigest(),
                    consumed_text_sha256=actual_hash,
                    preparation=preparation,
                    entity_counts=entity_counts,
                    relation_counts=relation_counts,
                    source_terms=dict(
                        Counter(
                            term.lower()
                            for term in re.findall(
                                r"poisson|binomial|normal|geometric|exponential|distribution",
                                source,
                                re.I,
                            )
                        )
                    ),
                    raw_extra_channels=sorted(set(raw) - {"entities", "relation_extraction"}),
                )
            )

        summary = dict(
            task_id=110,
            read_scope="ops.task_result/config and retained source projection only",
            release=release,
            no_author_labels_consumed=True,
            no_native_products_written=True,
            source_region_selection=selection,
            local_report_count=len(reports),
            local_execution_counts=dict(Counter(item["outcome"] for item in statuses)),
            raw_entity_counts=dict(entity_totals),
            raw_relation_counts=dict(relation_totals),
            raw_attribute_field_counts=dict(attribute_totals),
            reports=summaries,
            selected_region_links=[
                dict(
                    pointer=region["pointer"],
                    outcome=region["outcome"],
                    selections=region["selections"],
                    raw_report_contexts=[
                        index for index in region["selections"] if index in reconstructed
                    ],
                )
                for region in regions
                if region["pointer"] in selection["region_pointers"]
            ],
        )
        ROOT.joinpath("raw/parser-local-retained-diagnostic-001.json").write_text(
            json.dumps(summary, indent=2) + "\n"
        )

        cfg = M1Config.model_validate(config)
        original = json.loads(packs[reports[0]["pack"]]["declaration_json"])
        variants = {
            "current_three_entities_with_attributes": original,
            "same_three_entities_without_attributes": {
                key: value for key, value in original.items() if key != "entity_attributes"
            },
            "distribution_only_without_attributes": dict(
                entities=["distribution"], relations=original["relations"]
            ),
        }
        by_context = {item["context"]: item["report"] for item in reports}
        probe = dict(
            scope=(
                "six native calls on two exact retained source inputs; "
                "no quality or calibration claim"
            ),
            task_id=110,
            release=release,
            profile=dict(asdict(cfg.profile()), snapshot=str(cfg.profile().snapshot)),
            threshold=cfg.threshold,
            selected_contexts=[
                dict(
                    context=index,
                    declared_primary=primary,
                    owner=contexts[index]["region"],
                    source=reconstructed[index],
                )
                for primary, index in (("#/texts/25", 8), ("#/texts/325", 1))
            ],
            results=[],
        )
        worker = GlinerWorker(cfg.profile())
        try:
            for name, declaration in variants.items():
                pack = GlinerPack.from_declaration(release, declaration, version="native-local-v1")
                for index in (8, 1):
                    retained = by_context[index]
                    (report,) = worker.extract(
                        pack,
                        (
                            GlinerInput(
                                retained["context_id"],
                                retained["context_digest"],
                                reconstructed[index],
                            ),
                        ),
                        threshold=cfg.threshold,
                    )
                    probe["results"].append(
                        dict(variant=name, context=index, pack=asdict(pack), report=asdict(report))
                    )
            probe["outcome"] = "passed"
        except Exception as error:
            probe.update(outcome="failed", error=repr(error))
            raise
        finally:
            worker.close()
            ROOT.joinpath("raw/parser-local-schema-comparison-002.json").write_text(
                json.dumps(probe, indent=2) + "\n"
            )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
