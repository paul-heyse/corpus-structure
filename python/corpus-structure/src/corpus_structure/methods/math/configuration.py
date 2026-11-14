"""Pure mathematical source configuration shared by admitted and sealed readers."""

from pydantic import BaseModel, ConfigDict, Field

from corpus_structure.core.evidence import MacroDef

from .native import NativeDomainRule


class MathSection(BaseModel):
    """The pack's `math` section (D2 §12.1): the fallback macro map and the constants."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    macros: dict[str, str] = Field(default_factory=dict)
    constants: tuple[str, ...] = ()
    native_domain_rules: tuple[NativeDomainRule, ...] = ()

    def macro_table(self) -> dict[str, MacroDef]:
        return {name: MacroDef(body=body) for name, body in self.macros.items()}

