"""Transport adapter for the shared semantic selected-result query owner."""

from corpus_structure.semantic.demand_queries import (
    DemandQueryRequest,
    _cursor,
    _decode,
    serve_demand_query,
)

__all__ = ["DemandQueryRequest", "_cursor", "_decode", "serve_demand_query"]
