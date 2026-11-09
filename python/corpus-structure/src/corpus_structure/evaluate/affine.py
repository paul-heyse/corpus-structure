"""Protected comparison of an exact affine form, separate from source admission."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

import sympy
from lark import Token, Tree
from sympy.polys.polyerrors import BasePolynomialError

from corpus_structure.core.tex import token_form
from corpus_structure.core.vocab import ParseOutcome
from corpus_structure.methods.math import grammar
from corpus_structure.methods.math.prepared import PreparedMathInput
from corpus_structure.methods.math.transform import NotRepresentable
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.scientific_evidence import SIMPLIFY_SECONDS, scientific_model

POLICY = "pm2-exact-affine-1"


class _Undecided(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class NonzeroPremise:
    """An independently selected source or released policy reference for an inequality."""

    operand: PreparedMathInput
    evidence: str


def _read(operand: PreparedMathInput) -> Any:
    if not 0 < len(operand.latex) <= 512:
        raise _Undecided("operand exceeds affine input bounds")
    result = operand.reading()
    if result.failure is not None and result.failure.category == "timeout":
        raise _Undecided("mathematical reading timed out")
    if result.status is not ParseOutcome.OK:
        raise _Undecided(f"source interpretation is {result.status.value}")
    operand.definedness_result()
    return operand.symbolic_value()


def _formula(operand: PreparedMathInput, literal: str) -> PreparedMathInput:
    return PreparedMathInput(operand.context, literal, kind="formula", seconds=operand.seconds)


def assess_exact_affine(
    operand: PreparedMathInput,
    *,
    output: str,
    generator: str,
    coefficient: str,
    offset: str,
    nonzero: tuple[NonzeroPremise, ...] = (),
) -> dict[str, Any]:
    """Compare authored coefficient roles against a source-directed equation.

    The caller supplies a prepared, source-aligned context and independently
    authored expectations. Neither a positive comparison nor an explicit premise
    authenticates a declaration or authorizes admission.
    """
    context = operand.context
    grammar.require_main_thread()
    actual: dict[str, Any] = {}

    def report(outcome: str, detail: str) -> dict[str, Any]:
        tier = "undecided" if outcome == "undecided" else "symbolic"
        return (
            scientific_model()
            .validate_json(
                "ComparisonAssessment",
                canonical_bytes(
                    dict(
                        policy_id=POLICY,
                        evidence_profile=POLICY,
                        evidence_tier=tier,
                        decision_tier=tier,
                        agreement={
                            "equivalent": "agrees",
                            "different": "disagrees",
                            "undecided": "unknown",
                        }[outcome],
                        outcome=outcome,
                        numeric="not_run",
                        valid_points=0,
                        grammar=operand.state("interpretation").outcome or "not_read",
                        mechanism="sympy.Poly",
                        operands=[
                            canonical_bytes(dict(coefficient=coefficient, offset=offset)).decode(),
                            operand.latex,
                        ],
                        context=canonical_bytes(
                            dict(
                                exact_source=operand.source_text,
                                source_start=operand.source_start,
                                source_id=context.source_id,
                                scope=context.scope,
                                release=context.release_id,
                                interpretation=context.stage_key("symbolic"),
                                output=output,
                                generator=generator,
                                bindings=json.loads(context.bindings),
                                declarations=[asdict(item) for item in context.declarations],
                                assumptions=json.loads(context.assumptions),
                                nonzero=[
                                    dict(
                                        expression=p.operand.latex,
                                        source_start=p.operand.source_start,
                                        source_text=p.operand.source_text,
                                        evidence=p.evidence,
                                    )
                                    for p in nonzero
                                ],
                                sympy=sympy.__version__,
                                actual=actual,
                            ),
                        ).decode(),
                        detail=detail,
                    )
                ),
            )
            .model_dump(mode="json")
        )

    try:
        if not context.source_id or not context.scope or context.conflicts or context.unresolved:
            raise _Undecided("source scope or expression bindings are unresolved")
        if not 0 < operand.seconds <= SIMPLIFY_SECONDS:
            raise _Undecided("operand deadline exceeds the supported affine budget")
        if len(nonzero) > 8 or any(
            p.operand.context is not context or not p.evidence.strip() for p in nonzero
        ):
            raise _Undecided("nonzero premises exceed bounds or lack same-scope evidence")
        declarations = {}
        for declaration in context.declarations:
            if declaration.authority != "source" or declaration.role != "variable":
                continue
            if declaration.symbol in declarations:
                raise _Undecided("competing source declarations")
            declarations[declaration.symbol] = declaration
        if output == generator or not {output, generator} <= declarations.keys():
            raise _Undecided("output or generator has no unique source binding")
        if len(declarations) > 8:
            raise _Undecided("too many scoped affine symbols")
        symbols = {name: operand.premises.symbol(name) for name in declarations}
        dependent, variable = symbols[output], symbols[generator]
        parameters = tuple(
            value for name, value in symbols.items() if name not in {output, generator}
        )
        allowed = set(symbols.values())

        def exact_expr(value: Any) -> Any:
            if (
                not isinstance(value, sympy.Expr)
                or value.has(sympy.Float)
                or not value.free_symbols <= allowed
                or sympy.count_ops(value) > 96
                or any(
                    power.exp.is_Integer is not True or abs(power.exp) > 16
                    for power in value.atoms(sympy.Pow)
                )
            ):
                raise _Undecided("operand is outside exact bounded scalar algebra")
            return value

        def restrictions(value: PreparedMathInput) -> tuple[str, ...]:
            return value.unproved_definedness()

        with grammar.deadline(operand.seconds):
            equation = _read(operand)
            if not isinstance(equation, sympy.Equality):
                raise _Undecided("a directed equation is required")
            tree = operand.reading().tree
            relation = tree.children[0] if tree and len(tree.children) == 1 else None
            lhs = (
                relation.children[0]
                if isinstance(relation, Tree) and relation.data == "eq" and relation.children
                else None
            )
            if (
                not isinstance(lhs, Token)
                or token_form(str(lhs), context.macros) != output
                or equation.lhs != dependent
            ):
                raise _Undecided("equation lacks the selected source output on its left")
            rhs = exact_expr(equation.rhs)
            if dependent in rhs.free_symbols:
                raise _Undecided("equation is implicit in its output")

            # Match only exact polynomial nonzero premises (up to a nonzero
            # rational factor). No assumption is inferred by cancellation.
            def nonzero_key(value: Any) -> Any:
                poly = sympy.Poly(exact_expr(value), *symbols.values(), domain=sympy.QQ)
                if poly.is_zero or operand.premises.ask(sympy.Q.zero(value)) is True:
                    raise _Undecided("nonzero premise contradicts the scoped facts")
                return poly.monic()

            supported = set()
            for premise in nonzero:
                relation = _read(premise.operand)
                if not isinstance(relation, sympy.Unequality) or restrictions(premise.operand):
                    raise _Undecided("premise is not a defined exact nonzero relation")
                supported.add(nonzero_key(exact_expr(relation.lhs) - exact_expr(relation.rhs)))

            reference = (_formula(operand, coefficient), _formula(operand, offset))
            expected = tuple(exact_expr(_read(part)) for part in reference)
            for part in (operand, *reference):
                for restriction in restrictions(part):
                    if nonzero_key(_read(_formula(operand, restriction))) not in supported:
                        raise _Undecided("source denominator lacks a supported nonzero premise")
            if any(value.free_symbols - set(parameters) for value in expected):
                raise _Undecided("authored coefficient uses a non-parameter binding")

            domain = sympy.QQ.poly_ring(*parameters) if parameters else sympy.QQ
            polynomial = sympy.Poly(sympy.cancel(rhs), variable, domain=domain)
            degree = 0 if polynomial.is_zero else int(polynomial.degree())
            display = {value: sympy.Symbol(value.name) for value in symbols.values()}
            actual.update(
                degree=degree,
                coefficient=str(polynomial.nth(1).xreplace(display)),
                offset=str(polynomial.nth(0).xreplace(display)),
            )
            expected_polynomial = sympy.Poly(
                sympy.cancel(expected[0] * variable + expected[1]), variable, domain=domain
            )
            agrees = polynomial.terms() == expected_polynomial.terms()
        if not agrees:
            return report("different", "exact formal coefficient map differs")
        return report("equivalent", "exact formal coefficient map agrees")
    except grammar.Expired:
        return report("undecided", "exact affine assessment timed out")
    except (_Undecided, NotRepresentable, grammar.NotParsed, grammar.Ambiguous) as error:
        return report("undecided", str(error))
    except BasePolynomialError, ValueError, TypeError:
        return report("undecided", "expression is outside the admitted exact polynomial form")
