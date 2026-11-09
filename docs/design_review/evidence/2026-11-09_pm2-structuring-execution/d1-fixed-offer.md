# Private d1 fixed-offer rendering screen

**2026-11-09 · Test scope: exposed retained examples.** The [driver](fixed_offer_d1.py)
resolved the exact completed run/cut/task memberships, source-view and projection pins,
release declarations and report digests. It reused the incumbent's exact rendered state
and named questions, restoring order from the retained serialization and declaration
rather than from PostgreSQL object-key order. The task-wording arm changed only the
question wording. A separate arm reversed multiple offered options while preserving
the exact alternative keys and meanings. The quantity screen asked three independent
questions rather than claiming an equivalent paired grade. It preserved the authorized
source field and checked that each returned literal decoded within that field.

`uv run python docs/design_review/evidence/2026-11-09_pm2-structuring-execution/fixed_offer_d1.py`
passed on the pinned CUDA d1 worker. An [initial startup refusal](raw/d1-fixed-offer-initial-refusal.json)
settled without inference; the retry used the verified runtime identity. The worker
released shared GPU capacity on exit. The [screen receipt](raw/d1-fixed-offer-screen.json)
retains the exact inputs, question forms, and 15 native answers-by-request. No managed
inference run, new protected grade, model change, or selection was published.

| Control | Retained selection | Native result |
| --- | --- | --- |
| Fair-coin host | 431/531/2130 | The existing two offers include the `assign` host. Incumbent, task wording, and reordered task wording all returned `no_match`. |
| Gambler referent | 431/531/2131 | The exact `A gambler` candidate was present. Both arms returned `missing_referent`. |
| Exponential density | 464/572/2198 | The incumbent and both task-wording arms returned `no_match` with the literal rank-1 offer unchanged. |
| Negative-binomial | 464/572/2199 | All three arms returned `no_match`, preserving the genuine negative. |
| Roulette loss | 431/531/2129 | Incumbent and magnitude read both returned `1 dollar` without a native normalized number. The split arm correctly proposed `loss` but also returned `1 dollar` as the written unit, so it did not isolate the unit or the digit. |
| Fair-coin probability | 431/531/2128 | Incumbent preserved the exact `1/8` source literal which the historical ordinary path normalized to `0.125`. The separate magnitude read returned no span, so this arm regressed on the preservation control. |

Retain the incumbent. The screen does not establish a new qualified reading or assess
a new population. A future challenger should isolate exact amount/unit extraction before
reusing a generic quantity template, and independently qualify any proposal that changes
ordinary selection. Do not treat a successful native response or a high score as public
standing or protected evidence of gain.
