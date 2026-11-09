"""Preserve typed d1 answers, with source locations and selection authority separate."""

from __future__ import annotations

from math import isfinite

from corpus_structure.semantic.interpretation_questions import ANSWER_READS, QuestionFamily

from .pm2_products import ParserProduct


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
        binary = None
        if question.kind in ANSWER_READS:
            _probability(answer["found"])
            if answer["span"] is None:
                state = "unresolved"
            else:
                members = (key,)
                state = "proposed" if isinstance(located.get(key), MappedSource) else "unsupported"
                if question.kind in {"number", "date"}:
                    normalization = (
                        "unresolved"
                        if answer[question.kind] is None
                        else "native_proposal"
                        if state == "proposed"
                        else "unsupported"
                    )
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
            probabilities = answer["probabilities"]
            if set(probabilities) != set(offered):
                raise ValueError("d1 returned probabilities outside the offered alternatives")
            for probability in probabilities.values():
                _probability(probability)
            raw = answer["choices"] if question.multiple else [answer["choice"]]
            if len(raw) != len(set(raw)) or not set(raw) <= set(offered):
                raise ValueError("d1 returned an unoffered or repeated alternative")
            options = {option.key: option.disposition for option in question.options}
            observed_keys = tuple(option for option in offered if option in raw)
            for option in observed_keys:
                if (
                    question.minimum_probability is not None
                    and probabilities[option] < question.minimum_probability
                ):
                    states[option] = "policy_withheld"
                else:
                    states[option] = options.get(option, "proposed")
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
