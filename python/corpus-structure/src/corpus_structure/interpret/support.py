"""Corpus support for a claim from several sources (D5 §14.8).

Source `g` asserts the claim with likelihood ratio `r_g` when its extraction is right, and the
extraction is right with probability `pi_g`. An unreliable extraction carries no information,
so the source's factor is the mixture

    Lambda_g = pi_g r_g + (1 - pi_g)

Sources that copy one another (documents tracing to one report, models trained on one signal)
are not independent. With `k` sources and mean pairwise correlation `rho`, the effective count is
`k_eff = k / (1 + (k - 1) rho)`, and the support is

    log-odds = prior + (k_eff / k) * sum_g log Lambda_g

so twelve documents that trace to one source count once, not twelve times. Source reliability
`pi_g` comes from calibration or from the D5 §6 phase-2 Dawid-Skene estimate; this module does
not estimate it.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from corpus_structure.interpret.calibration import sigmoid


@dataclass(frozen=True, slots=True)
class SourceEvidence:
    source: str
    reliability: float  # pi_g
    likelihood_ratio: float  # r_g

    def __post_init__(self) -> None:
        if not 0.0 <= self.reliability <= 1.0:
            raise ValueError(f"{self.source}: reliability must lie in [0, 1]")
        if self.likelihood_ratio <= 0.0:
            raise ValueError(f"{self.source}: the likelihood ratio must be positive")

    @property
    def factor(self) -> float:
        return self.reliability * self.likelihood_ratio + (1.0 - self.reliability)


def effective_count(k: int, rho: float) -> float:
    if k < 0 or not 0.0 <= rho <= 1.0:
        raise ValueError("k must be non-negative and rho in [0, 1]")
    return 0.0 if k == 0 else k / (1.0 + (k - 1) * rho)


@dataclass(frozen=True, slots=True)
class Support:
    log_odds: float
    k: int
    k_eff: float

    @property
    def probability(self) -> float:
        return sigmoid(self.log_odds)


def corpus_support(
    prior_log_odds: float, sources: Sequence[SourceEvidence], rho: float = 0.0
) -> Support:
    k = len(sources)
    k_eff = effective_count(k, rho)
    total = sum(math.log(source.factor) for source in sources)
    discount = 1.0 if k == 0 else k_eff / k
    return Support(prior_log_odds + discount * total, k, k_eff)


def clustered_support(
    prior_log_odds: float, clusters: Sequence[Sequence[SourceEvidence]], rho_within: float
) -> Support:
    """Support where sources are grouped by provenance cluster (copies of one origin).

    Each cluster's sources are discounted by `rho_within`; distinct clusters are independent.
    """
    log_odds = prior_log_odds
    k = 0
    k_eff = 0.0
    for cluster in clusters:
        part = corpus_support(0.0, cluster, rho_within)
        log_odds += part.log_odds
        k += part.k
        k_eff += part.k_eff
    return Support(log_odds, k, k_eff)
