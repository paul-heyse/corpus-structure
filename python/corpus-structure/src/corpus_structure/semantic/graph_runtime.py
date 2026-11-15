"""One lazy import owner for the application's admitted native NetworkX execution.

Priority configuration is process-wide. Establish it once before selected graph
work, rather than changing it in request contexts or allowing ambient dispatch.
"""

import os

for _name in tuple(os.environ):
    if _name == "NETWORKX_BACKEND_PRIORITY" or _name.startswith(
        "NETWORKX_BACKEND_PRIORITY_"
    ) or _name == "NETWORKX_AUTOMATIC_BACKENDS":
        os.environ.pop(_name)

import networkx as nx  # noqa: E402

# A dictionary assignment replaces defaults AND function-specific priorities.
nx.config.backend_priority = {}
nx.config.fallback_to_nx = False

__all__ = ["nx"]
