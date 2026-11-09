"""Preserve typed d1 answers, with source locations and selection authority separate."""

from __future__ import annotations

import re
from decimal import Context, Decimal, DecimalException, Inexact
from itertools import islice
from math import isfinite

from corpus_structure.semantic.interpretation_questions import ANSWER_READS, QuestionFamily
from corpus_structure.semantic.metadata import decimal_projection
from corpus_structure.semantic.value_codec import decimal_text

from .pm2_products import ParserProduct


def render_candidate_options(
    family: QuestionFamily, rendered: list[dict]
) -> tuple[list[dict], dict]:
    """Put short provider-local labels beside the same bounded, located alternatives."""
    if not any(question.candidate_options for question in family.questions):
        return rendered, {}
    reserved = {option.key for question in family.questions for option in question.options}
    aliases = (f"option_{i}" for i in range(1, len(rendered) + len(reserved) + 1))
    aliases = (alias for alias in aliases if alias not in reserved)
    state, mapping = [], {}
    for candidate, alias in zip(rendered, islice(aliases, len(rendered)), strict=True):
        state.append({**candidate, "key": alias})
        mapping[alias] = candidate["key"]
    return state, mapping


_PLAIN_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)")
_PLAIN_RATIO = re.compile(r"([+-]?[0-9]+)/([0-9]+)")


def _exact_number(literal: str) -> str | None:
    """Normalize a bounded decimal or terminating ratio; make no locale/unit inference."""
    if len(literal) > 64:
        return None
    if _PLAIN_NUMBER.fullmatch(literal):
        value = decimal_projection(literal)
    elif (ratio := _PLAIN_RATIO.fullmatch(literal)) is not None:
        # This context bounds work and refuses rounding; a nonterminating value stays unresolved.
        context = Context(prec=256, traps=[Inexact])
        try:
            value = context.divide(Decimal(ratio[1]), Decimal(ratio[2])) if int(ratio[2]) else None
        except DecimalException:
            return None
    else:
        return None
    return None if value is None else decimal_text(value)


def _probability(value):
    if type(value) not in {int, float} or not isfinite(value) or not 0 <= value <= 1:
        raise ValueError("d1 returned an invalid probability")
    return value


def interpretation_products(
    family: QuestionFamily, request: dict, reply: dict, located: dict
) -> tuple[ParserProduct, ...]:
    from .pm2_source import MappedSource

    answers = reply["native"]["answers"]
    if set(answers) != set(request["questions"]):
        raise ValueError("d1 returned a different released question population")
    context = request["interpretation"]
    if context["declaration_digest"] != family.digest:
        raise ValueError("d1 request differs from its archived question declaration")
    candidates = context["candidates"]
    revised = context.get("version") in ("2", "3")
    aliases = context.get("option_aliases", {})
    if revised and any(q.candidate_options for q in family.questions):
        reserved = {option.key for q in family.questions for option in q.options}
        offered_keys = [row["key"] for row in request["state"].get("candidates", ())]
        if (
            set(aliases) & reserved
            or set(aliases.values()) & reserved
            or not len(aliases) == len(candidates) == len(offered_keys)
            or set(aliases) != set(offered_keys)
            or [aliases[key] for key in offered_keys]
            != [candidate["key"] for candidate in candidates]
        ):
            raise ValueError("d1 option labels differ from the retained candidate population")
    elif aliases:
        raise ValueError("d1 option labels require a versioned candidate choice")
    products = []
    for question in family.questions:
        key = question.key
        if key not in answers:
            continue
        answer = answers[key]
        if answer["type"] != question.kind:
            raise ValueError("d1 returned a different native answer kind")
        members = ()
        observed_keys = ()
        selected_keys = ()
        states = {}
        normalization = None
        normalized_value = None
        binary = None
        if question.kind in ANSWER_READS:
            _probability(answer["found"])
            if answer["span"] is None:
                state = "unresolved"
            else:
                members = (key,)
                mapped = located.get(key)
                state = "proposed" if isinstance(mapped, MappedSource) else "unsupported"
                if question.kind in {"number", "date"}:
                    normalization = (
                        "unresolved"
                        if answer[question.kind] is None
                        else "native_proposal"
                        if state == "proposed"
                        else "unsupported"
                    )
                if revised and question.kind == "number" and isinstance(mapped, MappedSource):
                    normalization = "unresolved"
                    if (
                        len(mapped.pieces) == 1
                        and mapped.anchors[0]["space"] == "native"
                        and mapped.anchors[0]["precision"] == "exact"
                    ):
                        normalized_value = _exact_number(mapped.pieces[0].quote)
                    if normalized_value is not None:
                        normalization = "source_exact"
        elif question.kind == "noul":
            probability = _probability(answer["noul"])
            direction = (
                "positive" if probability > 0.5 else "negative" if probability < 0.5 else "tie"
            )
            state = f"observed_{direction}"
            binary = {
                "direction": direction,
                "positive_probability": probability,
                "positive_criterion": question.positive,
                "negative_criterion": question.negative,
            }
        else:
            offered = request["questions"][key]["criteria"]
            if (
                revised
                and question.candidate_options
                and set(offered) != ({option.key for option in question.options} | set(aliases))
            ):
                raise ValueError("d1 choice differs from the retained option labels")
            probabilities = answer["probabilities"]
            if set(probabilities) != set(offered):
                raise ValueError("d1 returned probabilities outside the offered alternatives")
            for probability in probabilities.values():
                _probability(probability)
            raw = answer["choices"] if question.multiple else [answer["choice"]]
            if len(raw) != len(set(raw)) or not set(raw) <= set(offered):
                raise ValueError("d1 returned an unoffered or repeated alternative")
            options = {option.key: option.disposition for option in question.options}
            observed = tuple(option for option in offered if option in raw)
            question_aliases = aliases if question.candidate_options else {}
            observed_keys = tuple(question_aliases.get(option, option) for option in observed)
            for option, durable in zip(observed, observed_keys, strict=True):
                if (
                    question.minimum_probability is not None
                    and probabilities[option] < question.minimum_probability
                ):
                    states[durable] = "policy_withheld"
                else:
                    states[durable] = options.get(option, "proposed")
            selected_keys = tuple(
                option for option in observed_keys if states[option] == "proposed"
            )
            state = (
                "proposed"
                if selected_keys
                else next(iter(states.values()))
                if len(states) == 1
                else "unresolved"
            )
        value = {
            "question_key": key,
            "answer_kind": question.kind,
            "state": state,
            "native_answer": answer,
            "assessed_scope": context.get("assessed_scope"),
            "observed_keys": observed_keys,
            "selected_keys": selected_keys,
            "alternative_states": states,
            "candidates": candidates,
        }
        if normalization is not None:
            value["normalization"] = normalization
        if normalized_value is not None:
            value["normalized_value"] = normalized_value
        if revised and question.candidate_options:
            value["option_aliases"] = aliases
        if binary is not None:
            value["binary_observation"] = binary
        if context.get("focus") is not None:
            value["focus"] = context["focus"]
        if context.get("retrieval") is not None:
            value["retrieval"] = context["retrieval"]
        products.append(
            ParserProduct(
                f"interpretation:{key}", f"interpretation.{family.family}", value, members
            )
        )
    return tuple(products)
