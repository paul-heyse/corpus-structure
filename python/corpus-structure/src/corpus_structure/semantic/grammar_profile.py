"""Grammar reading kinds consumed by semantic scientific assessments."""

from corpus_structure.core.vocab import MathKind

GRAMMAR_KINDS = {
    "formula": MathKind.FORMULA,
    "relation": MathKind.RELATION,
    "member": MathKind.MEMBERSHIP,
    "set_expr": MathKind.SET,
    "list": MathKind.LIST,
}
