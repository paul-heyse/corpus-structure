"""Current served outcomes for selected, independently authored statistics meanings."""

import json

from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.query_compatibility import open_query_registry
from corpus_structure.serve.journey import serve_query

from .reference_scenarios import publish_reference_case

STAT = "https://corpus-structure.dev/domains/statistics/"


def entity(identity, class_name, label, *, local=False, attributes=()):
    supplied_attributes = list(attributes)
    if local and class_name == "RandomVariable":
        supplied_attributes.append(
            {
                "predicate": STAT + "symbol",
                "value": {"kind": "text", "text": label},
            }
        )
    item = {
        "id": identity,
        "class_iri": STAT + class_name,
        "label": label,
        "attributes": supplied_attributes,
    }
    if local:
        item["scope"] = {"extent": "statement", "locator": "reference.pdf#case-0"}
    return item


def formula(expression, *bindings):
    return {
        "kind": "formula",
        "language": "latex",
        "expression": expression,
        "bindings": list(bindings),
    }


def free_symbol(symbol):
    return {"kind": "free", "symbol": symbol}


def variable_symbol(symbol, entity_id):
    return {"kind": "variable", "symbol": symbol, "entity": entity_id}


def family_parameter_symbol(symbol, entity_id):
    return {"kind": "family_param", "symbol": symbol, "entity": entity_id}


def premise_parameter_symbol(symbol, claim_id, parameter, *, expression=False):
    return {
        "kind": "param_expr_of" if expression else "param_of",
        "symbol": symbol,
        "claim": claim_id,
        "parameter": parameter,
    }


def set_value(expression):
    return {"kind": "set", "language": "latex", "expression": expression, "bindings": []}


def param_values(**values):
    return {key: {"key": key, "value": value} for key, value in values.items()}


def family_parameter(identity, label, family, canonical_name):
    return entity(
        identity,
        "FamilyParameter",
        label,
        attributes=(
            {
                "predicate": STAT + "family",
                "value": {"kind": "entity", "target": family},
            },
            {
                "predicate": STAT + "canonical_name",
                "value": {"kind": "text", "text": canonical_name},
            },
        ),
    )


def claim(
    identity, subject, predicate, obj, *, quote, statement_role="conclusion", **qualification
):
    return {
        "id": identity,
        "subject": subject,
        "predicate": STAT + predicate,
        "object": {"kind": "entity", "target": obj} if isinstance(obj, str) else obj,
        "qualification": {"modality": "asserted", "polarity": True, **qualification},
        "establishment": "stated",
        "statement": "s",
        "statement_role": statement_role,
        "evidence": [{"quote": quote, "role": "primary"}],
    }


def batch(entities, claims, *, kind="definition"):
    return {
        "entities": entities,
        "claims": claims,
        "statements": [{"id": "s", "kind": kind, "anchor": "source-custody"}],
    }


def rows(conn, registry, run, name="claims", **params):
    answer = serve_query(conn, registry, name, params, run=run, max_rows=100)
    return json.loads(answer.model_dump_json())["rows"]


def entity_id(conn, registry, run, label):
    matched = rows(conn, registry, run, "entity", label=label)
    assert len(matched) == 1, (label, matched)
    return matched[0]["entity"]["entity_id"]


def publish_case(admin, writer, directory, paragraph, authored_batch):
    prepared, run, _ = publish_reference_case(
        admin, writer, directory, "statistics", [(paragraph, authored_batch)]
    )
    registry = open_query_registry(prepared, DOMAINS / "statistics")
    return prepared, run, registry


def test_trace_t1_current_construction_is_not_a_distribution_family(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path
):
    paragraph = (
        "For a real-valued Z, let X = a + b Z where a is real and b is positive; "
        "this is the location-scale family where a is the location parameter "
        "and b is the scale parameter."
    )
    entities = [
        entity("z", "RandomVariable", "Z", local=True),
        entity("x", "RandomVariable", "X", local=True),
        entity("location-scale", "FamilyConstruction", "location-scale family"),
        family_parameter("location", "location parameter", "location-scale", "location"),
        family_parameter("scale", "scale parameter", "location-scale", "scale"),
    ]
    claims = [
        claim(
            "z-real",
            "z",
            "takes_values_in",
            set_value("\\R"),
            quote="real-valued Z",
            modality="supposed",
        ),
        claim(
            "x-definition",
            "x",
            "defined_as",
            formula(
                "a + b Z",
                free_symbol("a"),
                free_symbol("b"),
                variable_symbol("Z", "z"),
            ),
            quote="X = a + b Z",
            modality="defined",
        ),
        claim(
            "construction-formula",
            "location-scale",
            "construction_formula",
            formula(
                "a + b Z",
                family_parameter_symbol("a", "location"),
                family_parameter_symbol("b", "scale"),
                variable_symbol("Z", "z"),
            ),
            statement_role="definiens",
            modality="defined",
            base_variable="z",
            param_symbols=param_values(
                location=formula("a", family_parameter_symbol("a", "location")),
                scale=formula("b", family_parameter_symbol("b", "scale")),
            ),
            condition={
                "kind": "member",
                "x": formula("b", family_parameter_symbol("b", "scale")),
                "set": set_value("(0, \\infty)"),
            },
            quote="X = a + b Z",
        ),
        claim(
            "location-role",
            "location",
            "parameter_role",
            {"kind": "text", "text": "location"},
            statement_role="definiens",
            quote="a is the location parameter",
        ),
        claim(
            "scale-role",
            "scale",
            "parameter_role",
            {"kind": "text", "text": "scale"},
            statement_role="definiens",
            quote="b is the scale parameter",
        ),
        claim(
            "construction-location",
            "location-scale",
            "has_parameter",
            "location",
            statement_role="definiens",
            quote="location parameter",
        ),
        claim(
            "construction-scale",
            "location-scale",
            "has_parameter",
            "scale",
            statement_role="definiens",
            quote="scale parameter",
        ),
        claim(
            "location-domain",
            "location",
            "parameter_domain",
            set_value("\\R"),
            statement_role="definiens",
            quote="a is real",
        ),
        claim(
            "scale-domain",
            "scale",
            "parameter_domain",
            set_value("(0, \\infty)"),
            statement_role="definiens",
            quote="b is positive",
        ),
    ]
    _prepared, run, registry = publish_case(
        semantic_db_engine,
        semantic_writer_engine,
        tmp_path,
        paragraph,
        batch(entities, claims),
    )
    with read_snapshot(semantic_reader_engine) as conn:
        construction_id = entity_id(conn, registry, run, "location-scale family")
        location_id = entity_id(conn, registry, run, "location parameter")
        scale_id = entity_id(conn, registry, run, "scale parameter")
        profile = rows(
            conn,
            registry,
            run,
            "construction_profile",
            construction="location-scale family",
        )
        all_claims = rows(conn, registry, run)
        construction_entities = rows(conn, registry, run, "entity", label="location-scale family")
        assert len(construction_entities) == 1
        membership_classes = {
            membership["class_iri"]
            for membership in construction_entities[0]["entity"]["memberships"]
        }
        assert STAT + "FamilyConstruction" in membership_classes
        assert STAT + "DistributionFamily" not in membership_classes
        properties = {row["fact"]["property_iri"] for row in profile}
        assert STAT + "construction_formula" in properties
        assert STAT + "has_parameter" in properties
        formulas = [
            row["fact"]
            for row in profile
            if row["fact"]["property_iri"] == STAT + "construction_formula"
        ]
        assert len(formulas) == 1
        assert formulas[0]["object"]["expression"] == "a + b Z"
        qualification = formulas[0]["qualification"]
        assert qualification["base_variable"] == entity_id(conn, registry, run, "Z")
        assert {
            key: entry["value"]["expression"]
            for key, entry in qualification["param_symbols"].items()
        } == {"location": "a", "scale": "b"}
        condition = qualification["condition"]
        assert condition["kind"] == "member"
        assert condition["x"]["expression"] == "b"
        assert condition["set"]["expression"] == "(0, \\infty)"
        assert {row["fact"]["subject"]["entity_id"] for row in profile} <= {
            construction_id,
            location_id,
            scale_id,
        }
        scale_domains = [
            row for row in all_claims if row["fact"]["property_iri"] == STAT + "parameter_domain"
        ]
        assert {
            (row["fact"]["subject"]["entity_id"], row["fact"]["object"]["expression"])
            for row in scale_domains
        } == {(location_id, "\\R"), (scale_id, "(0, \\infty)")}
        assert construction_id != scale_id and location_id != scale_id


def test_trace_t2_respectively_pairing_and_parameters_belong_to_family(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path
):
    paragraph = (
        "Suppose X has a normal distribution with location parameter mu and scale parameter sigma; "
        "location and scale are the mean and standard deviation, respectively."
    )
    entities = [
        entity("x", "RandomVariable", "X", local=True),
        entity("normal", "DistributionFamily", "normal distribution"),
        family_parameter("loc", "location parameter", "normal", "location"),
        family_parameter("scale", "scale parameter", "normal", "scale"),
        family_parameter("mean", "mean", "normal", "mean"),
        family_parameter("sd", "standard deviation", "normal", "standard_deviation"),
    ]
    claims = [
        claim(
            "normal-x",
            "x",
            "has_distribution",
            "normal",
            quote="X has a normal distribution",
            modality="supposed",
            param_values=param_values(
                location=formula("\\mu", family_parameter_symbol("mu", "loc")),
                scale=formula("\\sigma", family_parameter_symbol("sigma", "scale")),
            ),
        ),
        claim("normal-loc", "normal", "has_parameter", "loc", quote="location parameter"),
        claim("normal-scale", "normal", "has_parameter", "scale", quote="scale parameter"),
        claim(
            "normal-loc-mean",
            "loc",
            "identical_parameter",
            "mean",
            quote="location and scale are the mean and standard deviation, respectively",
        ),
        claim(
            "normal-scale-sd",
            "scale",
            "identical_parameter",
            "sd",
            quote="location and scale are the mean and standard deviation, respectively",
        ),
    ]
    _, run, registry = publish_case(
        semantic_db_engine,
        semantic_writer_engine,
        tmp_path,
        paragraph,
        batch(entities, claims, kind="remark"),
    )
    with read_snapshot(semantic_reader_engine) as conn:
        profile = rows(conn, registry, run, "family_profile", family="normal distribution")
        all_claims = rows(conn, registry, run)
        pairs = {
            (row["fact"]["subject"]["entity_id"], row["fact"]["object"])
            for row in profile
            if row["fact"]["property_iri"] == STAT + "identical_parameter"
        }
        assert pairs == {
            (
                entity_id(conn, registry, run, "location parameter"),
                entity_id(conn, registry, run, "mean"),
            ),
            (
                entity_id(conn, registry, run, "scale parameter"),
                entity_id(conn, registry, run, "standard deviation"),
            ),
        }
        family_parameters = {
            row["fact"]["object"]
            for row in profile
            if row["fact"]["property_iri"] == STAT + "has_parameter"
        }
        assert family_parameters == {
            entity_id(conn, registry, run, "location parameter"),
            entity_id(conn, registry, run, "scale parameter"),
        }
        random_variable_id = entity_id(conn, registry, run, "X")
        assert not any(
            row["fact"]["subject"]["entity_id"] == random_variable_id
            and row["fact"]["property_iri"] == STAT + "has_parameter"
            for row in all_claims
        )


def test_trace_t3_serves_supposed_premise_and_defers_derived_standard_deviation(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path
):
    paragraph = (
        "Suppose X is normal with mean mu and variance sigma squared; "
        "if a is real and b is nonzero, "
        "Y = a + b X is normal with mean a + b mu and variance b squared sigma squared."
    )
    entities = [
        entity("x", "RandomVariable", "X", local=True),
        entity("y", "RandomVariable", "Y", local=True),
        entity("normal", "DistributionFamily", "normal distribution"),
    ]
    claims = [
        claim(
            "premise",
            "x",
            "has_distribution",
            "normal",
            quote="Suppose X is normal with mean mu and variance sigma squared",
            modality="supposed",
            statement_role="premise",
            param_values=param_values(
                mean=formula("\\mu", free_symbol("mu")),
                variance=formula("\\sigma^2", free_symbol("sigma")),
            ),
        ),
        claim(
            "definition",
            "y",
            "defined_as",
            formula(
                "a + b X",
                free_symbol("a"),
                free_symbol("b"),
                variable_symbol("X", "x"),
            ),
            quote="Y = a + b X",
            modality="defined",
            condition={
                "kind": "all",
                "terms": [
                    {"kind": "member", "x": formula("a"), "set": set_value("\\R")},
                    {
                        "kind": "member",
                        "x": formula("b"),
                        "set": set_value("\\R \\setminus \\{0\\}"),
                    },
                ],
            },
            statement_role="definiens",
        ),
        claim(
            "transformed",
            "y",
            "has_distribution",
            "normal",
            quote="Y = a + b X is normal with mean a + b mu and variance b squared sigma squared",
            modality="asserted",
            param_values=param_values(
                mean=formula(
                    "a + b \\mu",
                    free_symbol("a"),
                    free_symbol("b"),
                    premise_parameter_symbol("mu", "premise", "mean"),
                ),
                variance=formula(
                    "b^2 \\sigma^2",
                    free_symbol("b"),
                    premise_parameter_symbol("sigma", "premise", "variance", expression=True),
                ),
            ),
            condition={
                "kind": "all",
                "terms": [
                    {"kind": "claim", "ref": "premise"},
                    {
                        "kind": "member",
                        "x": formula("a", free_symbol("a")),
                        "set": set_value("\\R"),
                    },
                    {
                        "kind": "member",
                        "x": formula("b", free_symbol("b")),
                        "set": set_value("\\R \\setminus \\{0\\}"),
                    },
                ],
            },
        ),
    ]
    _, run, registry = publish_case(
        semantic_db_engine,
        semantic_writer_engine,
        tmp_path,
        paragraph,
        batch(entities, claims, kind="theorem"),
    )
    with read_snapshot(semantic_reader_engine) as conn:
        transformations = rows(
            conn, registry, run, "transformations_of", family="normal distribution"
        )
        current_claims = rows(conn, registry, run, include_suppositions=True)
        assert len(transformations) == 1
        conclusion = transformations[0]["conclusion"]["fact"]
        premises = [premise["fact"] for premise in transformations[0]["premises"]]
        assert conclusion["subject"]["entity_id"] == entity_id(conn, registry, run, "Y")
        assert conclusion["property_iri"] == STAT + "has_distribution"
        assert conclusion["object"] == entity_id(conn, registry, run, "normal distribution")
        assert {
            key: entry["value"]["expression"]
            for key, entry in conclusion["qualification"]["param_values"].items()
        } == {"mean": "a + b \\mu", "variance": "b^2 \\sigma^2"}
        assert any(
            premise["subject"]["entity_id"] == entity_id(conn, registry, run, "X")
            and premise["qualification"]["modality"] == "supposed"
            for premise in premises
        )
        assert any(
            row["fact"]["subject"]["entity_id"] == entity_id(conn, registry, run, "X")
            and row["fact"]["qualification"]["modality"] == "supposed"
            for row in current_claims
        )
        assert not any(
            row["fact"]["property_iri"].endswith("/derived_from") for row in current_claims
        )
        transformed_values = [
            row["fact"]["qualification"].get("param_values", {})
            for row in current_claims
            if row["fact"]["subject"]["entity_id"] == entity_id(conn, registry, run, "Y")
            and row["fact"]["property_iri"] == STAT + "has_distribution"
        ]
        assert transformed_values and all(
            "standard_deviation" not in values for values in transformed_values
        )


def test_trace_t4_keeps_log_normal_parameters_distinct_from_normal_mean(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path
):
    paragraph = (
        "Suppose Y has a normal distribution with mean mu and standard deviation sigma; "
        "X = e to the Y has a lognormal distribution with parameters mu and sigma, "
        "where sigma is the shape parameter and e to the mu is the scale parameter."
    )
    entities = [
        entity("y", "RandomVariable", "Y", local=True),
        entity("x", "RandomVariable", "X", local=True),
        entity("normal", "DistributionFamily", "normal distribution"),
        entity("lognormal", "DistributionFamily", "lognormal distribution"),
        family_parameter("ln-mu", "mu parameter", "lognormal", "mu"),
        family_parameter("ln-sigma", "sigma parameter", "lognormal", "sigma"),
        family_parameter("ln-scale", "scale parameter", "lognormal", "scale"),
    ]
    claims = [
        claim(
            "normal-premise",
            "y",
            "has_distribution",
            "normal",
            quote="Y has a normal distribution with mean mu and standard deviation sigma",
            modality="supposed",
            statement_role="premise",
            param_values=param_values(
                mean=formula("\\mu", free_symbol("mu")),
                standard_deviation=formula("\\sigma", free_symbol("sigma")),
            ),
        ),
        claim(
            "x-definition",
            "x",
            "defined_as",
            formula("e^Y", free_symbol("e"), variable_symbol("Y", "y")),
            quote="X = e to the Y",
            modality="defined",
            statement_role="definiens",
        ),
        claim(
            "x-lognormal",
            "x",
            "has_distribution",
            "lognormal",
            quote="X = e to the Y has a lognormal distribution with parameters mu and sigma",
            modality="defined",
            statement_role="definiens",
            param_values=param_values(
                mu=formula("\\mu", family_parameter_symbol("mu", "ln-mu")),
                sigma=formula("\\sigma", family_parameter_symbol("sigma", "ln-sigma")),
            ),
            condition={"kind": "claim", "ref": "normal-premise"},
        ),
        claim(
            "sigma-shape",
            "ln-sigma",
            "parameter_role",
            {"kind": "text", "text": "shape"},
            quote="sigma is the shape parameter",
        ),
        claim(
            "lognormal-mu", "lognormal", "has_parameter", "ln-mu", quote="parameters mu and sigma"
        ),
        claim(
            "lognormal-sigma",
            "lognormal",
            "has_parameter",
            "ln-sigma",
            quote="parameters mu and sigma",
        ),
        claim("lognormal-scale", "lognormal", "has_parameter", "ln-scale", quote="scale parameter"),
        claim(
            "scale-derived",
            "ln-scale",
            "derived_parameter",
            formula(
                "e^\\mu",
                {"kind": "constant", "symbol": "e"},
                family_parameter_symbol("mu", "ln-mu"),
            ),
            quote="e to the mu is the scale parameter",
            modality="defined",
        ),
    ]
    _prepared, run, registry = publish_case(
        semantic_db_engine,
        semantic_writer_engine,
        tmp_path,
        paragraph,
        batch(entities, claims),
    )
    with read_snapshot(semantic_reader_engine) as conn:
        lognormal_id = entity_id(conn, registry, run, "lognormal distribution")
        mu_id = entity_id(conn, registry, run, "mu parameter")
        sigma_id = entity_id(conn, registry, run, "sigma parameter")
        scale_id = entity_id(conn, registry, run, "scale parameter")
        profile = rows(conn, registry, run, "family_profile", family="lognormal distribution")
        profile_claims = [row["fact"] for row in profile]
        parameter_pairs = {
            (fact["subject"]["entity_id"], fact["object"])
            for fact in profile_claims
            if fact["property_iri"] == STAT + "has_parameter"
        }
        assert parameter_pairs == {
            (lognormal_id, mu_id),
            (lognormal_id, sigma_id),
            (lognormal_id, scale_id),
        }
        assert {
            (fact["subject"]["entity_id"], fact["object"])
            for fact in profile_claims
            if fact["property_iri"] == STAT + "parameter_role"
        } == {(sigma_id, "shape")}
        assert {
            (fact["subject"]["entity_id"], fact["object"]["expression"])
            for fact in profile_claims
            if fact["property_iri"] == STAT + "derived_parameter"
        } == {(scale_id, "e^\\mu")}
        assert not any(
            fact["property_iri"] == STAT + "identical_parameter" for fact in profile_claims
        )
        all_claims = rows(conn, registry, run)
        lognormal_values = [
            row["fact"]["qualification"].get("param_values", {})
            for row in all_claims
            if row["fact"]["property_iri"] == STAT + "has_distribution"
            and row["fact"]["object"] == lognormal_id
        ]
        assert lognormal_values
        assert all(set(values) == {"mu", "sigma"} for values in lognormal_values)
        assert [
            {key: entry["value"]["expression"] for key, entry in values.items()}
            for values in lognormal_values
        ] == [{"mu": "\\mu", "sigma": "\\sigma"}]
