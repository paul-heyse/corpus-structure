"""Nominal contract for captured, receipt-bearing prepared effect capabilities.

The captured factory authenticates both the concrete wrapper and its wrapped
implementation. A subclass owns native receipt inspection for its declared
effect; this marker confers neither publication permission nor receipt validity.
"""

from abc import ABC, abstractmethod
from collections.abc import Generator
from typing import Any


class ReceiptBearingEffectPort(ABC):
    @abstractmethod
    def effect_implementation(self) -> Any:
        """Expose the concrete wrapped implementation for captured authentication."""
        raise NotImplementedError

    @abstractmethod
    def plan_python(
        self, values, *, binding=None, check_active, execution_owner
    ) -> Generator[Any, Any, Any]:
        """Return a completion only after authenticating the actual native effect."""
        raise NotImplementedError
