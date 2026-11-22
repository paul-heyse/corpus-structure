"""Native comparison over an already acquired annotation partition.

This query deliberately retains tagged extraction in its cost. The caller owns
the exact selected parent, established premises and the connection lifetime.
"""

import json

from sqlalchemy import text

_ROWS = """
WITH items AS MATERIALIZED (
    SELECT submitted, value
    FROM jsonb_array_elements(CAST(:body AS jsonb)->1)
         WITH ORDINALITY AS item(value, submitted)
), fields AS MATERIALIZED (
    SELECT submitted, jsonb_object_agg(pair->>0, pair->1) AS value
    FROM items CROSS JOIN LATERAL jsonb_array_elements(value->1) AS field(pair)
    GROUP BY submitted
), typed AS MATERIALIZED (
    SELECT submitted, value->'record_type'->>1 AS record_type,
           (value->'ordinal'->>1)::bigint AS ordinal,
           (value->'start'->>1)::bigint AS start,
           (value->'end'->>1)::bigint AS "end"
    FROM fields
)
"""


def annotation_membership(connection, body, addresses):
    """Return missing local item keys, after exact-parent acquisition by caller."""
    query = text(
        _ROWS
        + """
        SELECT requested.value->>0, (requested.value->>1)::bigint
        FROM jsonb_array_elements(CAST(:addresses AS jsonb)) AS requested(value)
        WHERE NOT EXISTS (
            SELECT FROM typed WHERE typed.record_type=requested.value->>0
            AND typed.ordinal=(requested.value->>1)::bigint
        )
        ORDER BY (requested.value->>0) COLLATE "C", (requested.value->>1)::bigint
        """
    )
    return tuple(
        connection.execute(query, {"body": json.dumps(body), "addresses": json.dumps(addresses)})
    )


def annotation_geometry(connection, body, extent):
    """Report bad spans and ordinals while retaining submitted row order."""
    query = text(
        _ROWS
        + """
        , ordered AS (
            SELECT *, row_number() OVER (
                PARTITION BY record_type ORDER BY submitted
            ) - 1 AS expected,
            lag(start) OVER (PARTITION BY record_type ORDER BY submitted) AS prior_start
            FROM typed
        )
        SELECT submitted, ordinal <> expected AS bad_ordinal,
               start < 0 OR "end" < start OR "end" > :extent AS bad_span,
               coalesce(start < prior_start, false) AS bad_order
        FROM ordered
        WHERE ordinal <> expected OR start < 0 OR "end" < start OR "end" > :extent
              OR start < prior_start
        ORDER BY submitted
        """
    )
    return tuple(connection.execute(query, {"body": json.dumps(body), "extent": extent}))
