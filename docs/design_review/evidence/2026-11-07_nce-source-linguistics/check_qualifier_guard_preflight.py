"""Exercise the complete proposed predicate admission function before native authoring."""

import argparse
import json
from pathlib import Path

from sqlalchemy import text

from corpus_structure.ingest.annotations import AnnotationProfile
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.scoped_relations import discover_relations
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import StructuralInput
from corpus_structure.semantic.structural_sources import load_structural_annotations
from corpus_structure.settings import Settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=int)
    parser.add_argument("configuration", type=Path)
    args = parser.parse_args()
    config = json.loads(args.configuration.read_bytes())["config"]
    inputs = StructuralInput.model_validate(config["inputs"])
    profile = AnnotationProfile(SentenceConfig.model_validate(config["sentences"]))
    settings = Settings()
    with open_runtime_engine(settings, "nce02-preflight-read", purpose="read") as engine:
        with read_snapshot(engine) as conn:
            originals = [
                (ref, load_structural_annotations(conn, inputs, ref.identity, profile))
                for ref in inputs.sources
            ]

    sql = Path("python/corpus-structure/src/corpus_structure/semantic/sql/source_contributions.sql")
    source = sql.read_text()
    start = source.index("CREATE OR REPLACE FUNCTION ops.validate_source_predicates(")
    end = source.index("\nREVOKE ALL ON FUNCTION ops.validate_source_predicates", start)
    checks = []
    with open_runtime_engine(settings, "nce02-preflight-native", purpose="maintenance") as engine:
        with engine.connect() as conn, conn.begin() as transaction:
            conn.exec_driver_sql(source[start:end])
            for ref, retained in originals:
                passages = tuple(p for p in inputs.passages if p.source_ref == ref.identity)
                output = discover_relations(
                    retained.source, annotations=retained.annotations,
                    annotation_errors=retained.errors, annotation_origin_task_id=retained.annotation_task_id,
                    passages=passages, predicate_version="3",
                )
                population = {
                    row["contribution_id"]: row for row in output["contributions"]
                    if row["semantic_type"].startswith("structural.predicate_")
                }
                options = {
                    **config,
                    "_predicate_version": "3",
                    "_predicate_operations": {
                        op["operation_key"]: op for op in output["extra_operations"]
                    },
                }
                result = conn.execute(text("""
                    SELECT ops.validate_source_predicates(t, v, CAST(:population AS jsonb),
                                                         CAST(:options AS jsonb))
                    FROM ops.task t JOIN kb.source_view v ON v.id=t.unit_id
                    WHERE t.run_id=:run AND t.unit_type='source_view' AND v.id=:view
                """), dict(population=json.dumps(population), options=json.dumps(options),
                           run=args.run, view=ref.source_view_id)).one()
                checks.append({"source_view": ref.source_view_id, "predicate_rows": len(population)})
            transaction.rollback()
    print(json.dumps(dict(outcome="passed", run=args.run, checked=checks)))


if __name__ == "__main__":
    main()
