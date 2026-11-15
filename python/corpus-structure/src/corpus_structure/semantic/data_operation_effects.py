"""Nominal contract for captured, receipt-bearing prepared effect capabilities.

The captured factory authenticates both the concrete wrapper and its wrapped
implementation. A subclass owns native receipt inspection for its declared
effect; this marker confers neither publication permission nor receipt validity.
"""

from abc import ABC, abstractmethod
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any


class CapturedEffectPort(ABC):
    @abstractmethod
    def effect_implementation(self) -> Any:
        """Expose the concrete wrapped implementation for captured authentication."""
        raise NotImplementedError

    @abstractmethod
    def plan_python(
        self, values, *, binding=None, check_active, execution_owner
    ) -> Generator[Any, Any, Any]:
        """Prepare a completion under the declared native effect's custody boundary."""
        raise NotImplementedError


class ReceiptBearingEffectPort(CapturedEffectPort):
    """A pre-completion effect must supply its already authenticated native receipt."""


class NativePublicationEffectPort(CapturedEffectPort):
    """The common native completion transaction performs the declared effect.

    Planning produces proposed outputs, without granting authority. Native admission
    independently checks the exact approved command/effect/factory and dependencies;
    only its committed common publication receipt establishes the effect.
    """


@dataclass(frozen=True)
class PreparedNativePublicationEffect(NativePublicationEffectPort):
    """Captured scalar preparation with authority deferred to native completion."""

    wrapped: Any

    def __post_init__(self):
        operation = self.wrapped.operation
        if (
            operation.profile != "command"
            or not operation.effects
            or operation.capabilities.preparation != "native-publication"
        ):
            raise ValueError("native publication preparation requires its declared command")

    def effect_implementation(self):
        return self.wrapped

    @property
    def operation(self):
        return self.wrapped.operation

    @property
    def identity(self):
        return self.wrapped.identity

    @property
    def native_selections(self):
        return self.wrapped.native_selections

    @property
    def consumer_receiver(self):
        return self.wrapped.consumer_receiver

    def plan_python(self, values, *, binding=None, check_active=lambda: None, execution_owner):
        return (
            yield from self.wrapped.plan_python(
                values,
                binding=binding,
                check_active=check_active,
                execution_owner=execution_owner,
            )
        )
