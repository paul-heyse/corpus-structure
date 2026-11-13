"""Resolve a successful original return through its declared completion semantics."""

from .data_operation_model import EffectiveOperation


def successful_return_outcome(operation: EffectiveOperation) -> str:
    """Choose exactly one admitted, effect-free successful terminal outcome.

    A returned value establishes normal completion, not which of several semantic
    success variants occurred. Such operations need an explicit result adapter.
    """
    from .data_operation_ports import PortRefusal

    candidates = []
    for outcome in operation.outcomes:
        mappings = tuple(
            transition
            for transition in operation.transitions
            if transition.dimension == "completion"
            and transition.before == "pending"
            and transition.outcome == outcome
            and transition.after in {"success", "empty", "failed"}
        )
        eligible = tuple(transition for transition in mappings if not transition.effects)
        if len(eligible) == 1 and eligible[0].after == "success":
            candidates.append(outcome)
        elif not mappings and outcome == "success":
            # The fixed native kernel permits the explicit terminal-state spelling
            # when there is no authored mapping. Never invent this spelling.
            candidates.append(outcome)
    if len(candidates) != 1:
        raise PortRefusal("successful return requires one unambiguous declared completion outcome")
    return candidates[0]
