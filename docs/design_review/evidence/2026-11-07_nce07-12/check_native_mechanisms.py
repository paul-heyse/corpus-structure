"""Read the retained attachment frame and compare exact SQL mutual ranks in rollback."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.neighbors import NearestNeighbors
from sqlalchemy import text

from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

SQL = (
    Path(__file__).resolve().parents[4]
    / "python/corpus-structure/src/corpus_structure/semantic/sql"
)


def isolated_function(conn, file, name, schema):
    body = (SQL / file).read_text()
    start = body.index(f"CREATE OR REPLACE FUNCTION {schema}.{name}(")
    end = body.index("$$;", body.index("AS $$", start)) + 3
    conn.exec_driver_sql(body[start:end].replace(f"FUNCTION {schema}.", "FUNCTION pg_temp.", 1))


def attachment_features(conn):
    isolated_function(
        conn, "operation_event_fitting.sql", "defining_text_event_features", "eval"
    )
    rows = conn.execute(
        text("""
          SELECT result->>'reason' AS reason,count(*) FROM (
           SELECT pg_temp.defining_text_event_features(c.task_id,c.contribution_id,c.source_view_id)
             AS result
           FROM kb.source_contribution c
           WHERE c.kind='relation' AND c.semantic_type='definition.defining_text_attachment'
             AND EXISTS(SELECT FROM ops.cut_task ct WHERE ct.origin_task_id=c.task_id AND ct.cut_id=245)
          ) events GROUP BY reason ORDER BY reason
        """)
    )
    counts = {reason or "eligible": count for reason, count in rows}
    if sum(counts.values()) != 82:
        raise ValueError("retained attachment population changed")
    return counts


def attachment_fit_control(conn, evaluation_id):
    """Validate protected frame and numeric digest parity with no retained fit write."""
    from corpus_structure.evaluate.operation_fitting import (
        NativeOperationEventFrame,
        fit_operation_event,
        frame_digest,
    )

    source = (SQL / "operation_event_fitting.sql").read_text()
    start = source.index("CREATE OR REPLACE FUNCTION eval.operation_event_fit_frame(")
    end = source.index("END $$;", start) + len("END $$;")
    definition = source[start:end].replace("eval.operation_event_fit_frame", "pg_temp.operation_event_fit_frame")
    definition = definition.replace("eval.defining_text_event_features", "pg_temp.defining_text_event_features")
    conn.exec_driver_sql(definition)
    frame_json, native_digest = conn.execute(
        text("""
        WITH frame AS MATERIALIZED (
          SELECT pg_temp.operation_event_fit_frame(
            :project,:evaluation,'defining_text_attachment_correctness') AS value)
        SELECT value,encode(sha256(convert_to(
           data.canonical_json(ops.contextual_identity_value(value->'frame')),'UTF8')),'hex')
        FROM frame
        """),
        {"project": "wce-gs120-method-development-20261106", "evaluation": evaluation_id},
    ).one()
    frame = NativeOperationEventFrame.model_validate_json(json.dumps(frame_json)).frame
    if frame_digest(frame) != native_digest:
        raise ValueError("native and Python frame digests differ")
    result = fit_operation_event(frame)
    if (result.status, result.positive, result.negative, result.origin_groups) != (
        "fitted", 1, 10, 1
    ):
        raise ValueError("protected development frame or fit differs")
    return dict(
        evaluation_id=evaluation_id, status=result.status, origin_groups=result.origin_groups,
        supported=result.positive, unsupported=result.negative, fit_persisted=False,
    )



def mutual_neighbors(conn):
    isolated_function(conn, "source_contributions.sql", "contextual_mutual_neighbors", "ops")
    # Six exactly tied boundary candidates, including two separately identified equal vectors.
    points = np.array(
        [[1, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [0, -1, 0], [0, 0, -1], [-1, 0, 0]],
        dtype=float,
    )
    targets = [
        dict(target_id=str(i), representation_digest=str(i), source_binding=str(i))
        for i in range(len(points))
    ]
    inventory = dict(
        inventory_id="controlled",
        targets=targets,
        semantic_groups=[
            dict(target_id="group-" + str(i), member_target_ids=[str(i)])
            for i in range(len(points))
        ],
    )
    vectors = [
        dict(
            object_id=str(i),
            source_binding=str(i),
            profile_id="controlled",
            representation_digest=str(i),
            values=p.tolist(),
        )
        for i, p in enumerate(points)
    ]

    def query(selected, vector_rows):
        return conn.execute(
            text("""
              SELECT pg_temp.contextual_mutual_neighbors(
                 CAST(:inventory AS jsonb),CAST(:profile AS jsonb),CAST(:vectors AS jsonb))
            """),
            {
                "inventory": json.dumps(selected),
                "profile": json.dumps(dict(profile_id="controlled", dimension=3)),
                "vectors": json.dumps(vector_rows),
            },
        ).scalar_one()

    ranked = NearestNeighbors(metric="cosine", algorithm="brute").fit(points)
    distances, indexes = ranked.kneighbors(X=None, n_neighbors=len(points) - 1)
    directed = {}
    for i, (peers, values) in enumerate(zip(indexes, distances, strict=True)):
        for rank, (distance, peer) in enumerate(sorted(zip(values, peers, strict=True))[:5], 1):
            directed[str(i), str(peer)] = (rank, distance)
    expected = {
        (a, b): (rank, directed[b, a][0], distance)
        for (a, b), (rank, distance) in directed.items()
        if a < b and (b, a) in directed
    }
    result = query(inventory, vectors)
    actual = {(e["left_id"], e["right_id"]): e for e in result["edges"]}
    if result["status"] != "completed" or actual.keys() != expected.keys():
        raise ValueError("mutual pair membership differs")
    for pair, (left, right, distance) in expected.items():
        edge = actual[pair]
        if (edge["left_rank"], edge["right_rank"]) != (left, right) or abs(
            edge["distance"] - distance
        ) > 1e-6:
            raise ValueError("mutual ranks or distance differ")
    for altered in (vectors[1:], [*vectors, vectors[0]], [dict(vectors[0], representation_digest="stale"), *vectors[1:]]):
        refused = query(inventory, altered)
        if refused["status"] != "vector_coverage_unavailable" or refused["edges"]:
            raise ValueError("invalid vector coverage produced a neighborhood")
    for count in (0, 1):
        small = query(
            dict(inventory, targets=targets[:count], semantic_groups=inventory["semantic_groups"][:count]),
            vectors[:count],
        )
        if small["status"] != "completed" or small["edges"]:
            raise ValueError("valid small selection must be empty")
    from corpus_structure.serve.contextual_navigation import verify_detached_neighborhood

    almost_collinear = [[1, 0, 0], [1, 0.0002, 0], [1, 0.0001, 0]]
    close_inventory = dict(
        inventory, targets=targets[:3], semantic_groups=inventory["semantic_groups"][:3]
    )
    close_vectors = [
        dict(vector, values=point)
        for vector, point in zip(vectors[:3], almost_collinear, strict=True)
    ]
    close = query(close_inventory, close_vectors)
    verify_detached_neighborhood(
        dict(
            neighborhood=close, inventories=[close_inventory],
            profiles=[dict(profile_id="controlled", dimension=3)], vectors=close_vectors,
        )
    )
    return dict(
        edges=len(actual), zero_distance=actual["0", "1"]["distance"],
        near_tie_detached_edges=len(close["edges"]),
    )


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation", type=int)
    args = parser.parse_args()
    with (
        open_runtime_engine(Settings(), "nce-mechanism-probe", purpose="maintenance") as engine,
        engine.connect() as conn,
    ):
        # Temporary definitions are connection-local. The connection rolls back on close.
        evidence = dict(attachment_features=attachment_features(conn), neighbors=mutual_neighbors(conn))
        if args.evaluation is not None:
            evidence["attachment_fit"] = attachment_fit_control(conn, args.evaluation)
        print(json.dumps(evidence))


if __name__ == "__main__":
    main()
