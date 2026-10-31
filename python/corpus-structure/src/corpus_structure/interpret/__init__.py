"""The interpretation layer: joint, calibrated use of stream outputs (D5 §14; ADR-0039).

Parser outputs are observations, not records. A record is accepted only from a posterior that
combines every stream's calibrated evidence with the template's constraints, against the record
type's acceptance threshold. The modules, bottom up:

- `records`: record types with value `v`, cost `c` and the threshold `tau = c / (c + v)`;
- `observations`: the observation store (alternatives, abstentions, score kind, provenance tags,
  config-hash cache keys) and layer masking by stream group;
- `calibration`: score -> likelihood ratio, per model, decision type and reliability grade;
- `decisions`: typed decisions whose options always include `UNKNOWN`, and split-conformal
  candidate-set sizing;
- `factors`: variables, log-space factors, hard constraints and exact inference within a
  factor-size budget;
- `lineage`: provenance polynomials evaluated in the Boolean, counting, Viterbi and
  why-provenance semirings, exact probability, invalidation and Fréchet bounds;
- `acceptance`: thresholds, expected utility and the expected value of information (EVI);
- `support`: corpus support from several sources with correlation-discounted counts;
- `harness`: the value function V(S) over stream groups, exact Shapley values, Möbius dividends,
  the Shapley interaction index, sequential gain decomposition and the document cluster bootstrap;
- `templates.numeric_reference`: prototype 1, a numeric reference resolved jointly with the
  value roles of the quantities it may denote.

The package depends on numpy and the standard library only; nothing in it imports a parser.
"""
