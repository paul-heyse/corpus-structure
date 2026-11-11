"""Released linguistic families and finite grammar-to-meaning bindings."""

from dataclasses import dataclass

REVISION = "tc-constructions-1"
FAMILIES = (
    "construction.predication",
    "construction.embedding",
    "construction.inflection",
    "construction.coordination",
    "construction.scope",
    "construction.clause_relation",
    "construction.attribution",
    "construction.function",
    "construction.source_readings",
)
GRAMMAR_FAMILIES = FAMILIES[:-1]
MODAL_FORCES = {
    "may": ("possibility", "permission"),
    "might": ("possibility",),
    "must": ("necessity", "obligation"),
    "can": ("ability", "possibility", "permission"),
    "could": ("ability", "possibility"),
    "should": ("recommendation", "expectation"),
    "would": ("conditional", "disposition"),
    "shall": ("obligation", "future"),
    "will": ("future", "disposition"),
}


@dataclass(frozen=True)
class Declaration:
    name: str
    family: str
    kind: str
    roles: tuple[str, ...]

    @property
    def rule_id(self) -> str:
        return (
            "tc.predication.verbal.v1"
            if self.name == "verbal_predication"
            else f"tc.{self.name}.v1"
        )


DECLARATIONS = {
    name: Declaration(name, FAMILIES[family], kind, roles)
    for name, family, kind, roles in (
        (
            "verbal_predication",
            0,
            "predicate",
            ("grammatical_subject", "predicate", "grammatical_object"),
        ),
        ("copular_predication", 0, "predicate", ("grammatical_subject", "copula", "complement")),
        ("adjectival_predication", 0, "predicate", ("grammatical_subject", "copula", "focus")),
        ("nominal_predication", 0, "predicate", ("focus",)),
        ("complement", 1, "predicate", ("grammatical_subject", "governor", "complement")),
        ("relative", 1, "predicate", ("antecedent", "relative_cue", "body")),
        ("nominal_modification", 1, "participant", ("head", "modifier")),
        ("attachment", 1, "participant", ("head", "attachment_cue", "modifier")),
        (
            "auxiliary_predication",
            2,
            "predicate",
            ("grammatical_subject", "auxiliary", "predicate", "grammatical_object"),
        ),
        (
            "passive_predication",
            2,
            "predicate",
            ("grammatical_subject", "auxiliary", "aspect", "predicate", "agent_cue", "agent"),
        ),
        ("coordination", 3, "operator", ("left", "connective", "right")),
        ("nominal_coordination", 3, "operator", ("left", "connective", "right")),
        ("negation", 4, "operator", ("cue", "target")),
        ("modality", 4, "operator", ("cue", "target")),
        (
            "modal_predication",
            4,
            "operator",
            ("grammatical_subject", "cue", "predicate", "grammatical_object"),
        ),
        ("quantification", 4, "binder", ("cue", "restrictor")),
        (
            "quantified_predication",
            4,
            "binder",
            ("cue", "restrictor", "predicate", "grammatical_object"),
        ),
        (
            "quantified_negative_predication",
            4,
            "binder",
            ("cue", "restrictor", "auxiliary", "negative_cue", "predicate", "grammatical_object"),
        ),
        (
            "negative_quantified_predication",
            4,
            "operator",
            ("quantifier_cue", "restrictor", "auxiliary", "cue", "predicate", "grammatical_object"),
        ),
        (
            "negative_predication",
            4,
            "operator",
            ("grammatical_subject", "auxiliary", "cue", "predicate", "grammatical_object"),
        ),
        (
            "conditional",
            5,
            "clause_relation",
            ("cue", "antecedent", "punctuation", "consequent_cue", "consequent"),
        ),
        ("clause_relation", 5, "clause_relation", ("left", "cue", "right")),
        ("reporting", 6, "attribution", ("reporter", "stance", "content")),
        ("quotation", 6, "attribution", ("open_quote", "content", "punctuation", "close_quote")),
        ("question", 7, "operator", ("content", "cue")),
        ("instruction", 7, "predicate", ("predicate", "grammatical_object")),
        ("passage_function", 7, "operator", ("cue", "content")),
        ("mention", 0, "participant", ("source",)),
        ("formal_atom", 0, "participant", ("source",)),
    )
}
