from __future__ import annotations

import re
import sys
from datetime import (
    date,
    datetime,
    time
)
from decimal import Decimal
from enum import Enum
from typing import (
    Any,
    ClassVar,
    Literal,
    Optional,
    Union
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer
)


metamodel_version = "1.12.0"
version = "0.2.0"


class ConfiguredBaseModel(BaseModel):
    model_config = ConfigDict(
        serialize_by_alias = True,
        validate_by_name = True,
        validate_assignment = True,
        validate_default = True,
        extra = "forbid",
        arbitrary_types_allowed = True,
        use_enum_values = True,
        strict = False,
    )





class LinkMLMeta(RootModel):
    root: dict[str, Any] = {}
    model_config = ConfigDict(frozen=True)

    def __getattr__(self, key:str):
        return getattr(self.root, key)

    def __getitem__(self, key:str):
        return self.root[key]

    def __setitem__(self, key:str, value):
        self.root[key] = value

    def __contains__(self, key:str) -> bool:
        return key in self.root


linkml_meta = LinkMLMeta({'default_prefix': 'core',
     'default_range': 'string',
     'description': "Q-1 probe copy of S4's core.yaml with "
                    'code/q1/model_patch.yaml applied.',
     'id': 'https://corpus-structure.dev/core',
     'imports': ['linkml:types'],
     'license': 'https://creativecommons.org/publicdomain/zero/1.0/',
     'name': 'core',
     'prefixes': {'ci': {'prefix_prefix': 'ci',
                         'prefix_reference': 'https://corpus-structure.dev/ci/'},
                  'core': {'prefix_prefix': 'core',
                           'prefix_reference': 'https://corpus-structure.dev/core/'},
                  'linkml': {'prefix_prefix': 'linkml',
                             'prefix_reference': 'https://w3id.org/linkml/'}},
     'source_file': '/home/paul/corpus-structure/docs/design_review/evidence/2026-10-28_phase0-model-probes/results/q1/schema/core_stage_b.yaml',
     'subsets': {'structural': {'description': 'Structural claims, about '
                                               'statements. They take no '
                                               'statement_role, are asserted, and '
                                               'carry no conditions (guideline '
                                               '§10.3, §10.6, §10.7 rule 4).',
                                'from_schema': 'https://corpus-structure.dev/core',
                                'name': 'structural'},
                 'unsupported': {'description': 'Something the source states that '
                                                'the schema cannot express; the '
                                                'claim has status unsupported (D1 '
                                                '§8.1).',
                                 'from_schema': 'https://corpus-structure.dev/core',
                                 'name': 'unsupported'}},
     'title': 'Core schema',
     'types': {'AuthoredAnchor': {'annotations': {'ci:py_type': {'tag': 'ci:py_type',
                                                                 'value': 'AuthoredAnchor'}},
                                  'description': '"unit", "outside" or a non-empty '
                                                 'tuple of sentence ids (authored '
                                                 'statement anchor).',
                                  'from_schema': 'https://corpus-structure.dev/core',
                                  'name': 'AuthoredAnchor',
                                  'typeof': 'string'},
               'LocalRef': {'annotations': {'ci:py_type': {'tag': 'ci:py_type',
                                                           'value': 'LocalRef'}},
                            'description': 'A batch-local reference; non-empty.',
                            'from_schema': 'https://corpus-structure.dev/core',
                            'name': 'LocalRef',
                            'typeof': 'string'},
               'NonEmpty': {'annotations': {'ci:py_type': {'tag': 'ci:py_type',
                                                           'value': 'NonEmptyStr'}},
                            'description': 'A non-empty string.',
                            'from_schema': 'https://corpus-structure.dev/core',
                            'name': 'NonEmpty',
                            'typeof': 'string'},
               'Offset': {'annotations': {'ci:py_type': {'tag': 'ci:py_type',
                                                         'value': 'Offset'}},
                          'description': "An offset in a rendition's canonical "
                                         'text.',
                          'from_schema': 'https://corpus-structure.dev/core',
                          'minimum_value': 0,
                          'name': 'Offset',
                          'typeof': 'integer'},
               'PrefixedName': {'annotations': {'ci:py_type': {'tag': 'ci:py_type',
                                                               'value': 'PrefixedName'}},
                                'description': 'A prefixed schema-element name.',
                                'from_schema': 'https://corpus-structure.dev/core',
                                'name': 'PrefixedName',
                                'pattern': '^[a-z][a-z0-9_]*:[A-Za-z_][A-Za-z0-9_]*$',
                                'typeof': 'string'},
               'SentenceId': {'annotations': {'ci:py_type': {'tag': 'ci:py_type',
                                                             'value': 'SentenceId'}},
                              'description': 'A sentence id (sN) or '
                                             'standing-context id (cN); a citation '
                                             'position.',
                              'from_schema': 'https://corpus-structure.dev/core',
                              'name': 'SentenceId',
                              'pattern': '^[sc][0-9]+$',
                              'typeof': 'string'},
               'StoredAnchor': {'annotations': {'ci:py_type': {'tag': 'ci:py_type',
                                                               'value': 'StoredAnchor'}},
                                'description': '"outside" or a non-empty tuple of '
                                               'segment keys (stored statement '
                                               'anchor).',
                                'from_schema': 'https://corpus-structure.dev/core',
                                'name': 'StoredAnchor',
                                'typeof': 'string'}}} )

class StatementKind(str, Enum):
    """
    What the source calls a statement (D1 §4.3).
    """
    definition = "definition"
    """
    Stipulates what a term means.
    """
    theorem = "theorem"
    """
    A stated result.
    """
    proposition = "proposition"
    """
    A stated result.
    """
    lemma = "lemma"
    """
    A stated auxiliary result.
    """
    corollary = "corollary"
    """
    A result stated to follow from another.
    """
    proof = "proof"
    """
    A proof of another statement.
    """
    example = "example"
    """
    A worked example with setup values.
    """
    exercise = "exercise"
    """
    An exercise with setup values and an asked quantity.
    """
    solution = "solution"
    """
    A solution of an exercise.
    """
    remark = "remark"
    """
    A remark; explicit claims only.
    """
    convention = "convention"
    """
    A convention the source adopts.
    """
    notation = "notation"
    """
    A notation the source introduces.
    """
    assumption = "assumption"
    """
    A statement whose only content is a supposition (a context premise).
    """
    narrative = "narrative"
    """
    Narrative text between units that states claims.
    """


class ClaimModality(str, Enum):
    """
    How the source holds a claim (D1 §5.2; guideline §10.6).
    """
    asserted = "asserted"
    """
    Concluded or stated as true; structural claims.
    """
    supposed = "supposed"
    """
    A supposition: suppose, assume, if, or let about something taken as given.
    """
    defined = "defined"
    """
    What a definition stipulates, including a formula introducing a variable.
    """
    conventional = "conventional"
    """
    A convention.
    """
    exemplified = "exemplified"
    """
    Setup values in examples and exercises.
    """
    posed = "posed"
    """
    Reserved until an asks_for predicate exists (OPEN-D2-15).
    """
    cited = "cited"
    """
    Attributed to another source.
    """


class Polarity(str, Enum):
    """
    Whether a claim is stated or denied.
    """
    positive = "positive"
    """
    Stated.
    """
    negative = "negative"
    """
    Denied.
    """


class StatementRole(str, Enum):
    """
    The part a claim plays in its statement (guideline §10.3).
    """
    premise = "premise"
    """
    A supposition the statement makes.
    """
    conclusion = "conclusion"
    """
    What a theorem, corollary or remark concludes.
    """
    definiens = "definiens"
    """
    What a definition stipulates, or a formula introducing a variable.
    """
    restriction = "restriction"
    """
    Reserved; restrictions are condition nodes in guideline v1.
    """
    example_value = "example_value"
    """
    A setup value of an example or exercise.
    """


class ScopeExtent(str, Enum):
    """
    How far a supposition or a local entity reaches.
    """
    statement = "statement"
    """
    The statement that states it.
    """
    section = "section"
    """
    The enclosing section from the stating sentence on.
    """
    document = "document"
    """
    The whole document.
    """


class BindKind(str, Enum):
    """
    The kinds of symbol binding (D1 §6.1).
    """
    variable = "variable"
    """
    The symbol denotes a local entity of the batch.
    """
    param_of = "param_of"
    """
    The symbol is the value of an entry of another claim's parameter map.
    """
    param_expr_of = "param_expr_of"
    """
    The symbol occurs inside the value of such an entry.
    """
    family_param = "family_param"
    """
    The symbol denotes a parameter entity of a family.
    """
    free = "free"
    """
    A symbol the statement introduces, restricted by its conditions.
    """
    constant = "constant"
    """
    A numeric or named constant.
    """
    unresolved = "unresolved"
    """
    Not bound; a counted resolution gap.
    """


class ParseStatus(str, Enum):
    """
    The math grammar's parse outcome for a value (D4 M11).
    """
    ok = "ok"
    """
    One reading.
    """
    partial = "partial"
    """
    Parsed in part.
    """
    ambiguous = "ambiguous"
    """
    More than one reading, none chosen by declared context.
    """
    failed = "failed"
    """
    Not parsed.
    """


class EvidenceRole(str, Enum):
    """
    The part an evidence span plays for its claim (guideline §10.8).
    """
    primary = "primary"
    """
    The minimal span that states the claim.
    """
    supporting = "supporting"
    """
    An introducer that determines the modality.
    """
    condition = "condition"
    """
    The span of a condition.
    """
    definition = "definition"
    """
    The span of a definition the claim relies on.
    """


class Relation(str, Enum):
    """
    Comparison relations of a cmp node.
    """
    LESS_THAN_SIGN = "<"
    """
    Less than.
    """
    LESS_THAN_SIGNEQUALS_SIGN = "<="
    """
    Less than or equal.
    """
    EQUALS_SIGN = "="
    """
    Equal.
    """
    EXCLAMATION_MARKEQUALS_SIGN = "!="
    """
    Not equal.
    """
    GREATER_THAN_SIGN = ">"
    """
    Greater than.
    """
    GREATER_THAN_SIGNEQUALS_SIGN = ">="
    """
    Greater than or equal.
    """


class EntityScope(str, Enum):
    """
    An entity's scope (vocab.EntityScope).
    """
    global_ = "global"
    """
    Global.
    """
    local = "local"
    """
    Local.
    """


class EntityExtent(str, Enum):
    """
    How far a local entity reaches.
    """
    statement = "statement"
    """
    The statement.
    """
    section = "section"
    """
    The section.
    """



class Entity(ConfiguredBaseModel):
    """
    Base of every entity class; instances are D1 entities.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'abstract': True, 'from_schema': 'https://corpus-structure.dev/core'})

    label: Optional[str] = Field(default=None, description="""Canonical display label (D1 §4.1). Identity follows the key rules of D1 §10.1.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'EntityItem']} })


class Statement(Entity):
    """
    An authored unit of meaning: a definition, theorem, proof, example, exercise, remark, convention or assumption. Claims belong to statements as premises, conclusions, definientia or example values. Listed in a batch's statements[], never in entities[].
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'annotations': {'ci:extract': {'tag': 'ci:extract', 'value': 'none'},
                         'ci:reify': {'tag': 'ci:reify', 'value': True},
                         'ci:scope': {'tag': 'ci:scope', 'value': 'local'}},
         'from_schema': 'https://corpus-structure.dev/core'})

    kind: Optional[StatementKind] = Field(default=None, description="""The statement's kind.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Statement', 'StatementItem']} })
    label: Optional[str] = Field(default=None, description="""Canonical display label (D1 §4.1). Identity follows the key rules of D1 §10.1.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'EntityItem']} })


class Value(ConfiguredBaseModel):
    """
    Base of the D1 value classes. Every value carries the tag t, which names its class; the core Pydantic value union is discriminated on it.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'abstract': True, 'from_schema': 'https://corpus-structure.dev/core'})

    t: Optional[str] = Field(default=None, description="""The value's tag, naming its class.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Value']} })


class Expression(Value):
    """
    A formula or set as written, with its symbol bindings (D1 §6.1).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'abstract': True,
         'annotations': {'ci:py_name': {'tag': 'ci:py_name', 'value': '_Expression'}},
         'from_schema': 'https://corpus-structure.dev/core',
         'slot_usage': {'t': {'equals_string_in': ['formula', 'set'], 'name': 't'}}})

    latex: str = Field(default=..., description="""The LaTeX exactly as written, macros included.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Expression']} })
    symbols: Optional[dict[str, SymbolBinding]] = Field(default=None, description="""The binding map, keyed by symbol in token form without backslash.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Expression']} })
    sympy: Optional[str] = Field(default=None, description="""The normalized SymPy form; added by M11 during consolidation.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:form': {'tag': 'ci:form', 'value': 'consolidated'}},
         'domain_of': ['Expression']} })
    parse: Optional[ParseStatus] = Field(default=None, description="""The parse outcome; added by M11 during consolidation.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:form': {'tag': 'ci:form', 'value': 'consolidated'}},
         'domain_of': ['Expression']} })
    t: Optional[Literal["formula", "set"]] = Field(default=None, description="""The value's tag, naming its class.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Value'], 'equals_string_in': ['formula', 'set']} })


class TextValue(Value):
    """
    Free text that is the value itself.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://corpus-structure.dev/core',
         'slot_usage': {'t': {'equals_string': 'text', 'name': 't'}}})

    v: str = Field(default=..., description="""The text.""", json_schema_extra = { "linkml_meta": {'domain_of': ['TextValue',
                       'NumberValue',
                       'BoolValue',
                       'EnumValue',
                       'DateValue']} })
    t: Optional[Literal["text"]] = Field(default=None, description="""The value's tag, naming its class.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Value'], 'equals_string': 'text'} })


class NumberValue(Value):
    """
    A number with its unit and basis as stated (D1 §6.2).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://corpus-structure.dev/core',
         'slot_usage': {'t': {'equals_string': 'number', 'name': 't'}}})

    v: str = Field(default=..., description="""The canonical decimal string.""", json_schema_extra = { "linkml_meta": {'domain_of': ['TextValue',
                       'NumberValue',
                       'BoolValue',
                       'EnumValue',
                       'DateValue']} })
    unit: Optional[str] = Field(default=None, description="""The unit as stated, or absent.""", json_schema_extra = { "linkml_meta": {'domain_of': ['NumberValue']} })
    basis: Optional[str] = Field(default=None, description="""A reference basis the source states, such as gauge or absolute, or absent.""", json_schema_extra = { "linkml_meta": {'domain_of': ['NumberValue']} })
    t: Optional[Literal["number"]] = Field(default=None, description="""The value's tag, naming its class.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Value'], 'equals_string': 'number'} })

    @field_validator('v')
    def pattern_v(cls, v):
        pattern=re.compile(r"^(?:0|-?(?:[1-9][0-9]*(?:\.[0-9]*[1-9])?|0\.[0-9]*[1-9]))$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.search(element):
                    err_msg = f"Invalid v format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.search(v):
            err_msg = f"Invalid v format: {v}"
            raise ValueError(err_msg)
        return v


class BoolValue(Value):
    """
    A truth value.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://corpus-structure.dev/core',
         'slot_usage': {'t': {'equals_string': 'bool', 'name': 't'}}})

    v: bool = Field(default=..., description="""The truth value.""", json_schema_extra = { "linkml_meta": {'domain_of': ['TextValue',
                       'NumberValue',
                       'BoolValue',
                       'EnumValue',
                       'DateValue']} })
    t: Optional[Literal["bool"]] = Field(default=None, description="""The value's tag, naming its class.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Value'], 'equals_string': 'bool'} })


class EnumValue(Value):
    """
    A permissible value of a schema enum.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://corpus-structure.dev/core',
         'slot_usage': {'t': {'equals_string': 'enum', 'name': 't'}}})

    enum: str = Field(default=..., description="""The enum's name.""", json_schema_extra = { "linkml_meta": {'domain_of': ['EnumValue']} })
    v: str = Field(default=..., description="""The permissible value.""", json_schema_extra = { "linkml_meta": {'domain_of': ['TextValue',
                       'NumberValue',
                       'BoolValue',
                       'EnumValue',
                       'DateValue']} })
    t: Optional[Literal["enum"]] = Field(default=None, description="""The value's tag, naming its class.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Value'], 'equals_string': 'enum'} })


class Formula(Expression):
    """
    A formula as written (D1 §6.1).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://corpus-structure.dev/core',
         'slot_usage': {'t': {'equals_string': 'formula', 'name': 't'}}})

    latex: str = Field(default=..., description="""The LaTeX exactly as written, macros included.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Expression']} })
    symbols: Optional[dict[str, SymbolBinding]] = Field(default=None, description="""The binding map, keyed by symbol in token form without backslash.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Expression']} })
    sympy: Optional[str] = Field(default=None, description="""The normalized SymPy form; added by M11 during consolidation.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:form': {'tag': 'ci:form', 'value': 'consolidated'}},
         'domain_of': ['Expression']} })
    parse: Optional[ParseStatus] = Field(default=None, description="""The parse outcome; added by M11 during consolidation.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:form': {'tag': 'ci:form', 'value': 'consolidated'}},
         'domain_of': ['Expression']} })
    t: Optional[Literal["formula"]] = Field(default=None, description="""The value's tag, naming its class.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Value'],
         'equals_string': 'formula',
         'equals_string_in': ['formula', 'set']} })


class SetExpr(Expression):
    """
    A set written in LaTeX.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'annotations': {'ci:py_name': {'tag': 'ci:py_name', 'value': 'SetValue'}},
         'from_schema': 'https://corpus-structure.dev/core',
         'slot_usage': {'t': {'equals_string': 'set', 'name': 't'}}})

    latex: str = Field(default=..., description="""The LaTeX exactly as written, macros included.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Expression']} })
    symbols: Optional[dict[str, SymbolBinding]] = Field(default=None, description="""The binding map, keyed by symbol in token form without backslash.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Expression']} })
    sympy: Optional[str] = Field(default=None, description="""The normalized SymPy form; added by M11 during consolidation.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:form': {'tag': 'ci:form', 'value': 'consolidated'}},
         'domain_of': ['Expression']} })
    parse: Optional[ParseStatus] = Field(default=None, description="""The parse outcome; added by M11 during consolidation.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:form': {'tag': 'ci:form', 'value': 'consolidated'}},
         'domain_of': ['Expression']} })
    t: Optional[Literal["set"]] = Field(default=None, description="""The value's tag, naming its class.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Value'],
         'equals_string': 'set',
         'equals_string_in': ['formula', 'set']} })


class DateValue(Value):
    """
    A date or date-time kept verbatim as ISO 8601.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://corpus-structure.dev/core',
         'slot_usage': {'t': {'equals_string': 'date', 'name': 't'}}})

    v: str = Field(default=..., description="""The ISO 8601 string as written.""", json_schema_extra = { "linkml_meta": {'domain_of': ['TextValue',
                       'NumberValue',
                       'BoolValue',
                       'EnumValue',
                       'DateValue']} })
    t: Optional[Literal["date"]] = Field(default=None, description="""The value's tag, naming its class.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Value'], 'equals_string': 'date'} })

    @field_validator('v')
    def pattern_v(cls, v):
        pattern=re.compile(r"^[0-9]{4}(-[0-9]{2}(-[0-9]{2}(T[0-9]{2}:[0-9]{2}(:[0-9]{2}(\.[0-9]+)?)?(Z|[+-][0-9]{2}:[0-9]{2})?)?)?)?$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.search(element):
                    err_msg = f"Invalid v format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.search(v):
            err_msg = f"Invalid v format: {v}"
            raise ValueError(err_msg)
        return v


class IntervalValue(Value):
    """
    An interval of values; an absent bound is unbounded.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://corpus-structure.dev/core',
         'slot_usage': {'t': {'equals_string': 'interval', 'name': 't'}}})

    start: Optional[Union[DateValue, Formula, NumberValue]] = Field(default=None, description="""The lower bound.""", json_schema_extra = { "linkml_meta": {'any_of': [{'range': 'NumberValue'},
                    {'range': 'DateValue'},
                    {'range': 'Formula'}],
         'domain_of': ['IntervalValue',
                       'PhraseValue',
                       'PhraseNode',
                       'Evidence',
                       'UnsupportedItem']} })
    end: Optional[Union[DateValue, Formula, NumberValue]] = Field(default=None, description="""The upper bound.""", json_schema_extra = { "linkml_meta": {'any_of': [{'range': 'NumberValue'},
                    {'range': 'DateValue'},
                    {'range': 'Formula'}],
         'domain_of': ['IntervalValue',
                       'PhraseValue',
                       'PhraseNode',
                       'Evidence',
                       'UnsupportedItem']} })
    start_incl: Optional[bool] = Field(default=None, description="""Whether the lower bound is included.""", json_schema_extra = { "linkml_meta": {'domain_of': ['IntervalValue']} })
    end_incl: Optional[bool] = Field(default=None, description="""Whether the upper bound is included.""", json_schema_extra = { "linkml_meta": {'domain_of': ['IntervalValue']} })
    t: Optional[Literal["interval"]] = Field(default=None, description="""The value's tag, naming its class.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Value'], 'equals_string': 'interval'} })


class PhraseValue(Value):
    """
    Text kept but not interpreted.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'annotations': {'ci:invariant': {'tag': 'ci:invariant',
                                          'value': 'ordered(start, end)'},
                         'ci:py_name': {'tag': 'ci:py_name', 'value': 'Phrase'}},
         'from_schema': 'https://corpus-structure.dev/core',
         'slot_usage': {'t': {'equals_string': 'phrase', 'name': 't'}}})

    text: str = Field(default=..., description="""The text as written.""", json_schema_extra = { "linkml_meta": {'domain_of': ['PhraseValue', 'PhraseNode']} })
    sentence: Optional[str] = Field(default=None, description="""The unit sentence (sN) or standing-context sentence (cN) holding the text.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:form': {'tag': 'ci:form', 'value': 'model'}},
         'domain_of': ['PhraseValue', 'PhraseNode', 'Evidence', 'UnsupportedItem']} })
    start: Optional[int] = Field(default=None, description="""Start offset in the rendition's canonical text.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:form': {'tag': 'ci:form', 'value': 'stored'},
                         'ci:required_in': {'tag': 'ci:required_in',
                                            'value': 'stored'}},
         'domain_of': ['IntervalValue',
                       'PhraseValue',
                       'PhraseNode',
                       'Evidence',
                       'UnsupportedItem']} })
    end: Optional[int] = Field(default=None, description="""End offset in the rendition's canonical text.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:form': {'tag': 'ci:form', 'value': 'stored'},
                         'ci:required_in': {'tag': 'ci:required_in',
                                            'value': 'stored'}},
         'domain_of': ['IntervalValue',
                       'PhraseValue',
                       'PhraseNode',
                       'Evidence',
                       'UnsupportedItem']} })
    coarse: Optional[bool] = Field(default=None, description="""The text was not located exactly; the span is the whole cited sentence.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:form': {'tag': 'ci:form', 'value': 'stored'}},
         'domain_of': ['PhraseValue', 'PhraseNode', 'Evidence', 'UnsupportedItem']} })
    t: Optional[Literal["phrase"]] = Field(default=None, description="""The value's tag, naming its class.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Value'], 'equals_string': 'phrase'} })


class EntityRef(ConfiguredBaseModel):
    """
    A reference to an entity, a local ref or an entity key once stored.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://corpus-structure.dev/core'})

    ref: str = Field(default=..., description="""The local ref or entity key.""", json_schema_extra = { "linkml_meta": {'domain_of': ['EntityRef', 'ClaimNode']} })


class SymbolBinding(ConfiguredBaseModel):
    """
    How one symbol of a formula is bound (D1 §6.1).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'annotations': {'ci:validator': {'tag': 'ci:validator',
                                          'value': 'binding_fields'}},
         'from_schema': 'https://corpus-structure.dev/core'})

    symbol: str = Field(default=..., description="""The symbol in token form, without backslash (the map key).""", json_schema_extra = { "linkml_meta": {'domain_of': ['SymbolBinding', 'EntityItem']} })
    bind: BindKind = Field(default=..., description="""The binding kind.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SymbolBinding']} })
    entity: Optional[str] = Field(default=None, description="""variable, family_param: the entity's local ref (key once stored).""", json_schema_extra = { "linkml_meta": {'domain_of': ['SymbolBinding']} })
    claim: Optional[str] = Field(default=None, description="""param_of, param_expr_of: the claim's local ref (key once stored).""", json_schema_extra = { "linkml_meta": {'domain_of': ['SymbolBinding']} })
    param: Optional[str] = Field(default=None, description="""param_of, param_expr_of: the entry of the claim's ci:param_map qualifier.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SymbolBinding']} })


class Condition(ConfiguredBaseModel):
    """
    A condition tree (D1 §7), discriminated on op.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'abstract': True, 'from_schema': 'https://corpus-structure.dev/core'})

    op: str = Field(default=..., description="""The node's tag.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Condition']} })


class AndNode(Condition):
    """
    Conjunction.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'annotations': {'ci:py_name': {'tag': 'ci:py_name', 'value': 'And'}},
         'from_schema': 'https://corpus-structure.dev/core',
         'slot_usage': {'op': {'equals_string': 'and', 'name': 'op'}}})

    args: list[Condition] = Field(default=..., description="""The conjuncts.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AndNode', 'OrNode', 'PredNode']} })
    op: Literal["and"] = Field(default=..., description="""The node's tag.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Condition'], 'equals_string': 'and'} })


class OrNode(Condition):
    """
    Disjunction.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'annotations': {'ci:py_name': {'tag': 'ci:py_name', 'value': 'Or'}},
         'from_schema': 'https://corpus-structure.dev/core',
         'slot_usage': {'op': {'equals_string': 'or', 'name': 'op'}}})

    args: list[Condition] = Field(default=..., description="""The disjuncts.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AndNode', 'OrNode', 'PredNode']} })
    op: Literal["or"] = Field(default=..., description="""The node's tag.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Condition'], 'equals_string': 'or'} })


class NotNode(Condition):
    """
    Negation.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'annotations': {'ci:py_name': {'tag': 'ci:py_name', 'value': 'Not'}},
         'from_schema': 'https://corpus-structure.dev/core',
         'slot_usage': {'op': {'equals_string': 'not', 'name': 'op'}}})

    arg: Condition = Field(default=..., description="""The negated node.""", json_schema_extra = { "linkml_meta": {'domain_of': ['NotNode']} })
    op: Literal["not"] = Field(default=..., description="""The node's tag.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Condition'], 'equals_string': 'not'} })


class ForallNode(Condition):
    """
    Universal quantification over a set.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'annotations': {'ci:py_name': {'tag': 'ci:py_name', 'value': 'Forall'}},
         'from_schema': 'https://corpus-structure.dev/core',
         'slot_usage': {'op': {'equals_string': 'forall', 'name': 'op'}}})

    var: str = Field(default=..., description="""The bound variable.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ForallNode']} })
    set: SetExpr = Field(default=..., description="""The set.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ForallNode', 'MemberNode']} })
    body: Condition = Field(default=..., description="""The body.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ForallNode']} })
    op: Literal["forall"] = Field(default=..., description="""The node's tag.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Condition'], 'equals_string': 'forall'} })


class ClaimNode(Condition):
    """
    A reference to another claim of the batch.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://corpus-structure.dev/core',
         'slot_usage': {'op': {'equals_string': 'claim', 'name': 'op'}}})

    ref: str = Field(default=..., description="""The claim's local ref.""", json_schema_extra = { "linkml_meta": {'domain_of': ['EntityRef', 'ClaimNode']} })
    op: Literal["claim"] = Field(default=..., description="""The node's tag.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Condition'], 'equals_string': 'claim'} })


class MemberNode(Condition):
    """
    Set membership.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://corpus-structure.dev/core',
         'slot_usage': {'op': {'equals_string': 'member', 'name': 'op'}}})

    x: Formula = Field(default=..., description="""The element.""", json_schema_extra = { "linkml_meta": {'domain_of': ['MemberNode']} })
    set: SetExpr = Field(default=..., description="""The set.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ForallNode', 'MemberNode']} })
    op: Literal["member"] = Field(default=..., description="""The node's tag.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Condition'], 'equals_string': 'member'} })


class CmpNode(Condition):
    """
    A comparison.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://corpus-structure.dev/core',
         'slot_usage': {'op': {'equals_string': 'cmp', 'name': 'op'}}})

    rel: Relation = Field(default=..., description="""The relation.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CmpNode']} })
    lhs: Formula = Field(default=..., description="""Left side.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CmpNode']} })
    rhs: Formula = Field(default=..., description="""Right side.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CmpNode']} })
    op: Literal["cmp"] = Field(default=..., description="""The node's tag.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Condition'], 'equals_string': 'cmp'} })


class PredNode(Condition):
    """
    A schema predicate over arguments.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://corpus-structure.dev/core',
         'slot_usage': {'op': {'equals_string': 'pred', 'name': 'op'}}})

    name: str = Field(default=..., description="""The predicate name.""", json_schema_extra = { "linkml_meta": {'domain_of': ['PredNode']} })
    args: list[Union[EntityRef, Formula]] = Field(default=..., description="""The arguments, entity references or formulas.""", min_length=1, json_schema_extra = { "linkml_meta": {'any_of': [{'range': 'EntityRef'}, {'range': 'Formula'}],
         'domain_of': ['AndNode', 'OrNode', 'PredNode']} })
    op: Literal["pred"] = Field(default=..., description="""The node's tag.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Condition'], 'equals_string': 'pred'} })


class PhraseNode(Condition):
    """
    A condition kept as text.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'annotations': {'ci:invariant': {'tag': 'ci:invariant',
                                          'value': 'ordered(start, end)'}},
         'from_schema': 'https://corpus-structure.dev/core',
         'slot_usage': {'op': {'equals_string': 'phrase', 'name': 'op'}}})

    text: str = Field(default=..., description="""The text.""", json_schema_extra = { "linkml_meta": {'domain_of': ['PhraseValue', 'PhraseNode']} })
    sentence: Optional[str] = Field(default=None, description="""The citing sentence.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:form': {'tag': 'ci:form', 'value': 'model'}},
         'domain_of': ['PhraseValue', 'PhraseNode', 'Evidence', 'UnsupportedItem']} })
    start: Optional[int] = Field(default=None, description="""Start offset.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:form': {'tag': 'ci:form', 'value': 'stored'},
                         'ci:required_in': {'tag': 'ci:required_in',
                                            'value': 'stored'}},
         'domain_of': ['IntervalValue',
                       'PhraseValue',
                       'PhraseNode',
                       'Evidence',
                       'UnsupportedItem']} })
    end: Optional[int] = Field(default=None, description="""End offset.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:form': {'tag': 'ci:form', 'value': 'stored'},
                         'ci:required_in': {'tag': 'ci:required_in',
                                            'value': 'stored'}},
         'domain_of': ['IntervalValue',
                       'PhraseValue',
                       'PhraseNode',
                       'Evidence',
                       'UnsupportedItem']} })
    coarse: Optional[bool] = Field(default=None, description="""Not located exactly.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:form': {'tag': 'ci:form', 'value': 'stored'}},
         'domain_of': ['PhraseValue', 'PhraseNode', 'Evidence', 'UnsupportedItem']} })
    op: Literal["phrase"] = Field(default=..., description="""The node's tag.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Condition'], 'equals_string': 'phrase'} })


class UnsupportedNode(PhraseNode):
    """
    A condition the schema cannot express.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://corpus-structure.dev/core',
         'slot_usage': {'op': {'equals_string': 'unsupported', 'name': 'op'}}})

    reason: str = Field(default=..., description="""Why it is unsupported.""", json_schema_extra = { "linkml_meta": {'domain_of': ['UnsupportedNode', 'AlternativeItem', 'UnsupportedItem']} })
    text: str = Field(default=..., description="""The text.""", json_schema_extra = { "linkml_meta": {'domain_of': ['PhraseValue', 'PhraseNode']} })
    sentence: Optional[str] = Field(default=None, description="""The citing sentence.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:form': {'tag': 'ci:form', 'value': 'model'}},
         'domain_of': ['PhraseValue', 'PhraseNode', 'Evidence', 'UnsupportedItem']} })
    start: Optional[int] = Field(default=None, description="""Start offset.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:form': {'tag': 'ci:form', 'value': 'stored'},
                         'ci:required_in': {'tag': 'ci:required_in',
                                            'value': 'stored'}},
         'domain_of': ['IntervalValue',
                       'PhraseValue',
                       'PhraseNode',
                       'Evidence',
                       'UnsupportedItem']} })
    end: Optional[int] = Field(default=None, description="""End offset.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:form': {'tag': 'ci:form', 'value': 'stored'},
                         'ci:required_in': {'tag': 'ci:required_in',
                                            'value': 'stored'}},
         'domain_of': ['IntervalValue',
                       'PhraseValue',
                       'PhraseNode',
                       'Evidence',
                       'UnsupportedItem']} })
    coarse: Optional[bool] = Field(default=None, description="""Not located exactly.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:form': {'tag': 'ci:form', 'value': 'stored'}},
         'domain_of': ['PhraseValue', 'PhraseNode', 'Evidence', 'UnsupportedItem']} })
    op: Literal["unsupported"] = Field(default=..., description="""The node's tag.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Condition'], 'equals_string': 'unsupported'} })


class MapEntry(ConfiguredBaseModel):
    """
    One entry of a map qualifier (ci:object map): a string key and a value. A map qualifier ranges over a subclass, multivalued and inlined, and is written as an object from key to value.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'abstract': True, 'from_schema': 'https://corpus-structure.dev/core'})

    key: str = Field(default=..., description="""The entry's key.""", json_schema_extra = { "linkml_meta": {'domain_of': ['MapEntry', 'IdentityEntry']} })
    value: Optional[str] = Field(default=None, description="""The entry's value.""", json_schema_extra = { "linkml_meta": {'domain_of': ['MapEntry', 'IdentityEntry']} })


class CoreQualifiers(ConfiguredBaseModel):
    """
    The core qualifiers; schema qualifiers are extra slots, raw JSON until S1 types them.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'annotations': {'ci:py_name': {'tag': 'ci:py_name', 'value': 'Qualifiers'},
                         'ci:validator': {'tag': 'ci:validator',
                                          'value': 'stored: '
                                                   'schema_qualifiers_prefixed'}},
         'extra_slots': {'allowed': True},
         'from_schema': 'https://corpus-structure.dev/core'})

    modality: Optional[ClaimModality] = Field(default=ClaimModality("asserted"), description="""How the source holds the claim (D1 §5.2); asserted when absent.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:role': {'tag': 'ci:role', 'value': 'qualifier'}},
         'domain_of': ['CoreQualifiers'],
         'ifabsent': 'string(asserted)'} })
    polarity: Optional[Polarity] = Field(default=Polarity("positive"), description="""Whether the claim is stated or denied; positive when absent.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:role': {'tag': 'ci:role', 'value': 'qualifier'}},
         'domain_of': ['CoreQualifiers'],
         'ifabsent': 'string(positive)'} })
    hedge: Optional[PhraseValue] = Field(default=None, description="""A hedging phrase the source attaches to the claim (\"usually\", \"in some settings\").""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:role': {'tag': 'ci:role', 'value': 'qualifier'}},
         'domain_of': ['CoreQualifiers']} })
    attribution: Optional[Entity] = Field(default=None, description="""Who the source says states the claim, when it cites someone.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:role': {'tag': 'ci:role', 'value': 'qualifier'}},
         'domain_of': ['CoreQualifiers']} })
    conditions: Optional[Condition] = Field(default=None, description="""The condition tree under which the claim holds (D1 §7).""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:role': {'tag': 'ci:role', 'value': 'qualifier'}},
         'domain_of': ['CoreQualifiers']} })
    scope: Optional[ScopeExtent] = Field(default=None, description="""How far a supposition reaches beyond its statement; model-facing a ScopeExtent value, stored {extent, segment}.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:role': {'tag': 'ci:role', 'value': 'qualifier'},
                         'ci:stored_range': {'tag': 'ci:stored_range',
                                             'value': 'StoredScope'}},
         'domain_of': ['CoreQualifiers', 'EntityItem']} })
    valid_time: Optional[IntervalValue] = Field(default=None, description="""The time interval over which the claim holds, when the source states one.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:role': {'tag': 'ci:role', 'value': 'qualifier'}},
         'domain_of': ['CoreQualifiers']} })


class StoredScope(ConfiguredBaseModel):
    """
    The stored scope qualifier, its extent and the segment it resolves to.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'annotations': {'ci:form': {'tag': 'ci:form', 'value': 'stored'}},
         'from_schema': 'https://corpus-structure.dev/core'})

    extent: ScopeExtent = Field(default=..., description="""The extent.""", json_schema_extra = { "linkml_meta": {'domain_of': ['StoredScope', 'EntityItem']} })
    segment: str = Field(default=..., description="""The segment key.""", json_schema_extra = { "linkml_meta": {'domain_of': ['StoredScope']} })


class Evidence(ConfiguredBaseModel):
    """
    An evidence span of a claim.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'annotations': {'ci:invariant': {'tag': 'ci:invariant',
                                          'value': 'ordered(start, end)'}},
         'from_schema': 'https://corpus-structure.dev/core'})

    sentence: Optional[str] = Field(default=None, description="""The cited sentence.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:form': {'tag': 'ci:form', 'value': 'model'},
                         'ci:required_in': {'tag': 'ci:required_in', 'value': 'model'}},
         'domain_of': ['PhraseValue', 'PhraseNode', 'Evidence', 'UnsupportedItem']} })
    quote: Optional[str] = Field(default=None, description="""The quote.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:form': {'tag': 'ci:form', 'value': 'model'},
                         'ci:required_in': {'tag': 'ci:required_in', 'value': 'model'}},
         'domain_of': ['Evidence', 'UnsupportedItem']} })
    start: Optional[int] = Field(default=None, description="""Start offset.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:form': {'tag': 'ci:form', 'value': 'stored'},
                         'ci:required_in': {'tag': 'ci:required_in',
                                            'value': 'stored'}},
         'domain_of': ['IntervalValue',
                       'PhraseValue',
                       'PhraseNode',
                       'Evidence',
                       'UnsupportedItem']} })
    end: Optional[int] = Field(default=None, description="""End offset.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:form': {'tag': 'ci:form', 'value': 'stored'},
                         'ci:required_in': {'tag': 'ci:required_in',
                                            'value': 'stored'}},
         'domain_of': ['IntervalValue',
                       'PhraseValue',
                       'PhraseNode',
                       'Evidence',
                       'UnsupportedItem']} })
    role: EvidenceRole = Field(default=..., description="""The span's role.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Evidence']} })
    coarse: Optional[bool] = Field(default=None, description="""Not located exactly.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:form': {'tag': 'ci:form', 'value': 'stored'}},
         'domain_of': ['PhraseValue', 'PhraseNode', 'Evidence', 'UnsupportedItem']} })


class IdentityEntry(MapEntry):
    """
    One identity slot of an entity, slot to local ref or literal.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://corpus-structure.dev/core'})

    key: str = Field(default=..., description="""The identity slot.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:stored_range': {'tag': 'ci:stored_range',
                                             'value': 'PrefixedName'}},
         'domain_of': ['MapEntry', 'IdentityEntry']} })
    value: str = Field(default=..., description="""The local ref or literal.""", json_schema_extra = { "linkml_meta": {'domain_of': ['MapEntry', 'IdentityEntry']} })


class EntityItem(ConfiguredBaseModel):
    """
    An entity item of a batch.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'annotations': {'ci:invariant': {'tag': 'ci:invariant',
                                          'value': 'stored: iff_present(scope_segment, '
                                                   'scope = local)'},
                         'ci:py_name': {'tag': 'ci:py_name', 'value': 'Entity'},
                         'ci:validator': {'tag': 'ci:validator',
                                          'value': 'extent_only_local'}},
         'from_schema': 'https://corpus-structure.dev/core'})

    local_ref: str = Field(default=..., description="""The local ref.""", json_schema_extra = { "linkml_meta": {'domain_of': ['EntityItem', 'StatementItem', 'ClaimItem', 'UnsupportedItem']} })
    type: str = Field(default=..., description="""The entity class.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:stored_range': {'tag': 'ci:stored_range',
                                             'value': 'PrefixedName'}},
         'domain_of': ['EntityItem']} })
    label: str = Field(default=..., description="""The label.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'EntityItem']} })
    scope: EntityScope = Field(default=..., description="""The scope.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CoreQualifiers', 'EntityItem']} })
    extent: Optional[EntityExtent] = Field(default=None, description="""A local entity's extent.""", json_schema_extra = { "linkml_meta": {'domain_of': ['StoredScope', 'EntityItem']} })
    symbol: Optional[str] = Field(default=None, description="""The symbol.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SymbolBinding', 'EntityItem']} })
    aliases: Optional[list[str]] = Field(default=None, description="""Aliases.""", json_schema_extra = { "linkml_meta": {'domain_of': ['EntityItem']} })
    identity: Optional[dict[str, Union[str, IdentityEntry]]] = Field(default=None, description="""Identity slots.""", json_schema_extra = { "linkml_meta": {'domain_of': ['EntityItem']} })
    scope_segment: Optional[str] = Field(default=None, description="""The segment a local entity is scoped to.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:form': {'tag': 'ci:form', 'value': 'stored'}},
         'domain_of': ['EntityItem']} })


class StatementItem(ConfiguredBaseModel):
    """
    A statement item of a batch.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'annotations': {'ci:py_name': {'tag': 'ci:py_name', 'value': 'Statement'}},
         'from_schema': 'https://corpus-structure.dev/core'})

    local_ref: str = Field(default=..., description="""The local ref.""", json_schema_extra = { "linkml_meta": {'domain_of': ['EntityItem', 'StatementItem', 'ClaimItem', 'UnsupportedItem']} })
    kind: str = Field(default=..., description="""The statement kind.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Statement', 'StatementItem']} })
    anchor: str = Field(default=..., description="""The anchor.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:stored_range': {'tag': 'ci:stored_range',
                                             'value': 'StoredAnchor'}},
         'domain_of': ['StatementItem']} })


class ClaimItem(ConfiguredBaseModel):
    """
    A claim item of a batch.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'annotations': {'ci:py_name': {'tag': 'ci:py_name', 'value': 'Claim'}},
         'from_schema': 'https://corpus-structure.dev/core'})

    local_ref: str = Field(default=..., description="""The local ref.""", json_schema_extra = { "linkml_meta": {'domain_of': ['EntityItem', 'StatementItem', 'ClaimItem', 'UnsupportedItem']} })
    predicate: str = Field(default=..., description="""The predicate.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:stored_range': {'tag': 'ci:stored_range',
                                             'value': 'PrefixedName'}},
         'domain_of': ['ClaimItem']} })
    subject: str = Field(default=..., description="""The subject's local ref.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClaimItem']} })
    statement: Optional[str] = Field(default=None, description="""The statement's local ref.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClaimItem']} })
    statement_role: Optional[StatementRole] = Field(default=None, description="""The claim's role in its statement.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClaimItem']} })
    object: Union[EntityRef, Value] = Field(default=..., description="""The object.""", json_schema_extra = { "linkml_meta": {'any_of': [{'range': 'EntityRef'}, {'range': 'Value'}],
         'domain_of': ['ClaimItem']} })
    qualifiers: Optional[CoreQualifiers] = Field(default=None, description="""The qualifiers.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ClaimItem']} })
    evidence: list[Evidence] = Field(default=..., description="""The evidence.""", min_length=1, json_schema_extra = { "linkml_meta": {'domain_of': ['ClaimItem']} })


class AlternativeItem(ConfiguredBaseModel):
    """
    Alternative readings of the same text.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://corpus-structure.dev/core'})

    refs: list[str] = Field(default=..., description="""The alternatives.""", min_length=2, json_schema_extra = { "linkml_meta": {'domain_of': ['AlternativeItem']} })
    reason: str = Field(default=..., description="""Why.""", json_schema_extra = { "linkml_meta": {'domain_of': ['UnsupportedNode', 'AlternativeItem', 'UnsupportedItem']} })


class UnsupportedItem(ConfiguredBaseModel):
    """
    Something the source states that the schema cannot express.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'annotations': {'ci:invariant': {'tag': 'ci:invariant',
                                          'value': 'ordered(start, end)'},
                         'ci:py_name': {'tag': 'ci:py_name', 'value': 'Unsupported'}},
         'from_schema': 'https://corpus-structure.dev/core'})

    start: Optional[int] = Field(default=None, description="""Start offset.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:form': {'tag': 'ci:form', 'value': 'stored'},
                         'ci:required_in': {'tag': 'ci:required_in',
                                            'value': 'stored'}},
         'domain_of': ['IntervalValue',
                       'PhraseValue',
                       'PhraseNode',
                       'Evidence',
                       'UnsupportedItem']} })
    end: Optional[int] = Field(default=None, description="""End offset.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:form': {'tag': 'ci:form', 'value': 'stored'},
                         'ci:required_in': {'tag': 'ci:required_in',
                                            'value': 'stored'}},
         'domain_of': ['IntervalValue',
                       'PhraseValue',
                       'PhraseNode',
                       'Evidence',
                       'UnsupportedItem']} })
    local_ref: str = Field(default=..., description="""The local ref.""", json_schema_extra = { "linkml_meta": {'domain_of': ['EntityItem', 'StatementItem', 'ClaimItem', 'UnsupportedItem']} })
    sentence: Optional[str] = Field(default=None, description="""The sentence.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:form': {'tag': 'ci:form', 'value': 'model'},
                         'ci:required_in': {'tag': 'ci:required_in', 'value': 'model'}},
         'domain_of': ['PhraseValue', 'PhraseNode', 'Evidence', 'UnsupportedItem']} })
    quote: Optional[str] = Field(default=None, description="""The quote.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:form': {'tag': 'ci:form', 'value': 'model'},
                         'ci:required_in': {'tag': 'ci:required_in', 'value': 'model'}},
         'domain_of': ['Evidence', 'UnsupportedItem']} })
    reason: str = Field(default=..., description="""Why.""", json_schema_extra = { "linkml_meta": {'domain_of': ['UnsupportedNode', 'AlternativeItem', 'UnsupportedItem']} })
    coarse: Optional[bool] = Field(default=None, description="""Not located exactly.""", json_schema_extra = { "linkml_meta": {'annotations': {'ci:form': {'tag': 'ci:form', 'value': 'stored'}},
         'domain_of': ['PhraseValue', 'PhraseNode', 'Evidence', 'UnsupportedItem']} })


class Batch(ConfiguredBaseModel):
    """
    A batch envelope.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'annotations': {'ci:validator': {'tag': 'ci:validator',
                                          'value': 'well_formed_batch'}},
         'from_schema': 'https://corpus-structure.dev/core'})

    unit_ref: str = Field(default=..., description="""The unit ref.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Batch']} })
    entities: Optional[list[EntityItem]] = Field(default=None, description="""Entities.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Batch']} })
    statements: Optional[list[StatementItem]] = Field(default=None, description="""Statements.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Batch']} })
    claims: Optional[list[ClaimItem]] = Field(default=None, description="""Claims.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Batch']} })
    alternatives: Optional[list[AlternativeItem]] = Field(default=None, description="""Alternatives.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Batch']} })
    unsupported: Optional[list[UnsupportedItem]] = Field(default=None, description="""Unsupported items.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Batch']} })


# Model rebuild
# see https://pydantic-docs.helpmanual.io/usage/models/#rebuilding-a-model
Entity.model_rebuild()
Statement.model_rebuild()
Value.model_rebuild()
Expression.model_rebuild()
TextValue.model_rebuild()
NumberValue.model_rebuild()
BoolValue.model_rebuild()
EnumValue.model_rebuild()
Formula.model_rebuild()
SetExpr.model_rebuild()
DateValue.model_rebuild()
IntervalValue.model_rebuild()
PhraseValue.model_rebuild()
EntityRef.model_rebuild()
SymbolBinding.model_rebuild()
Condition.model_rebuild()
AndNode.model_rebuild()
OrNode.model_rebuild()
NotNode.model_rebuild()
ForallNode.model_rebuild()
ClaimNode.model_rebuild()
MemberNode.model_rebuild()
CmpNode.model_rebuild()
PredNode.model_rebuild()
PhraseNode.model_rebuild()
UnsupportedNode.model_rebuild()
MapEntry.model_rebuild()
CoreQualifiers.model_rebuild()
StoredScope.model_rebuild()
Evidence.model_rebuild()
IdentityEntry.model_rebuild()
EntityItem.model_rebuild()
StatementItem.model_rebuild()
ClaimItem.model_rebuild()
AlternativeItem.model_rebuild()
UnsupportedItem.model_rebuild()
Batch.model_rebuild()
