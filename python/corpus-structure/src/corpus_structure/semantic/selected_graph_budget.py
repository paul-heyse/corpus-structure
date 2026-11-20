"""Refusal shared by selected graph acquisition and semantic projection."""


class SelectedGraphBudgetExceeded(ValueError):
    """The authenticated closure exceeds the caller's whole-examination budget."""

    def __init__(self, message, *, cut):
        super().__init__(message)
        self.cut = cut
