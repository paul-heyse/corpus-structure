"""Explicit release inputs and boundary arithmetic for the analytical projection."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
from hashlib import sha256
from pathlib import Path

import yaml

from .types import PreparedRelease, ResolvedDependencies, SourceArtifact, SourceBundle

PROFILE_NAME = "analytical-profile.json"
_MODEL = Path(__file__).resolve().parents[1] / "model" / "semantic"


def analytical_inputs(
    bundle: SourceBundle, dependencies: ResolvedDependencies = ResolvedDependencies()
) -> tuple[SourceBundle, ResolvedDependencies]:
    """Opt into the packaged profile through ordinary hashed, archived release inputs."""
    return (
        SourceBundle("analytical-root", (*bundle.sources,
            SourceArtifact("analytics", (_MODEL / "analytics.yaml").read_bytes()),
            SourceArtifact("analytical-root", yaml.safe_dump({
                "id": "https://corpus-structure.dev/semantic/analytical-root",
                "name": "semantic_analytical_root", "imports": [bundle.root, "analytics"],
            }).encode()),
        )),
        ResolvedDependencies(
            (*dependencies.artifacts, SourceArtifact(PROFILE_NAME, (_MODEL / PROFILE_NAME).read_bytes())),
            dependencies.vocabularies,
            dependencies.ontology_sources,
        ),
    )


@dataclass(frozen=True)
class AnalyticalProfile:
    digest: str
    precision: int = 38
    scale: int = 12

    @classmethod
    def from_release(cls, prepared: PreparedRelease) -> AnalyticalProfile:
        content = next((a.content for a in prepared.artifacts if a.kind == PROFILE_NAME), None)
        if content is None:
            raise ValueError("release has no admitted analytical profile")
        model = prepared.validate_json("AnalyticalProfile", content)
        fields = model.model_dump()
        if fields != {"version": "analytical-1", "precision": 38, "scale": 12,
                       "rounding": "HALF_EVEN", "overflow": "refuse"}:
            raise ValueError("unsupported analytical compiler profile")
        return cls(sha256(content).hexdigest(), fields["precision"], fields["scale"])

    def decimal(self, lexical: str) -> tuple[Decimal, bool]:
        """Quantize once with an explicit context; reject nonfinite and bounded overflow."""
        value = Decimal(lexical)
        if not value.is_finite() or (value and value.adjusted() >= self.precision - self.scale):
            raise ValueError("value outside analytical DECIMAL(38,12)")
        context = Context(prec=self.precision, rounding=ROUND_HALF_EVEN)
        try:
            result = value.quantize(Decimal((0, (1,), -self.scale)), context=context)
        except InvalidOperation as exc:
            raise ValueError("value outside analytical DECIMAL(38,12)") from exc
        if result and result.adjusted() >= self.precision - self.scale:
            raise ValueError("rounded value outside analytical DECIMAL(38,12)")
        return result, result != value

    def quotient(self, numerator: Decimal, denominator: Decimal) -> tuple[Decimal, bool]:
        """Correctly round an exact rational at the boundary without binary floating point."""
        if not numerator.is_finite() or not denominator.is_finite() or not denominator:
            raise ValueError("quotient requires finite numbers and nonzero denominator")
        # Scale integer ratios exactly, avoiding a finite-context division double rounding.
        n, nd = numerator.as_integer_ratio()
        d, dd = denominator.as_integer_ratio()
        n, d = n * dd * 10**self.scale, nd * d
        if d < 0:
            n, d = -n, -d
        magnitude, remainder = divmod(abs(n), d)
        if 2 * remainder > d or (2 * remainder == d and magnitude % 2):
            magnitude += 1
        if magnitude >= 10**self.precision:
            raise ValueError("quotient outside analytical DECIMAL(38,12)")
        with localcontext(Context(prec=self.precision, rounding=ROUND_HALF_EVEN)):
            result = Decimal((-1 if n < 0 else 1) * magnitude).scaleb(-self.scale)
        return result, remainder != 0
