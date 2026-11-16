"""Current contribution inventory from exact selected DDO products and members."""


def read_demand_contributions(connection, request):
    """Current contribution inventory from exact native product/member selections.

    Operation standing is independent of member cardinality. Parent packets and
    member addresses retain actual producing episodes and required source context.
    """
    from .demand_queries import serve_demand_query

    return serve_demand_query(connection, request)
