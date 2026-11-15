"""Selected characterization witness vocabulary shared by extraction and admission.

These are projection roles, not RDF predicates or data-operation support edges.
Protected task matching retains its own question/choice interpretation.
"""

ASSESSMENT_COLLECTIONS = ("occurrences", "annotations", "memberships", "roles", "terms", "choices", "coverage")
ASSESSMENT_NODE_KINDS = (*ASSESSMENT_COLLECTIONS, "choice_member", "named_binding", "native_runs")
ASSESSMENT_RELATION_KINDS = tuple(sorted({
    "choice_group", "owner", "member", "group", "root", "occurrences", "premises",
    "required_choices", "external_premises", "required_external_choices", "head", "members", "antecedent_members",
    *(name + "." + field for name in ("native_token", "native_mention", "native_edu") for field in ("native_run", "container", "sentence")),
    "named_match.native_container", "named_match.nodes", "named_match.binding", "named_match.negation_occurrences",
    "navigation.roles.occurrences", "navigation.source_labels.occurrences", "navigation.native_tokens.native_node",
    "formal_input.correspondence.source_occurrences", "formal_input.parent_occurrence", "formal.input_id", "formal.symbol_parent", "scope",
    "basis.premises", "basis.choice_refs", "basis.external_premises", "basis.required_external_choices", "child", "alternative",
}))

# Reified task questions are a distinct projection of the same source facts.
# They preserve assertion and choice incidence instead of renaming source nodes.
TASK_ASSESSMENT_NODE_KINDS = ("entity", "assertion", "group", "member")
TASK_ASSESSMENT_RELATION_KINDS = ("subject", "object", "requires", "member", "root")
