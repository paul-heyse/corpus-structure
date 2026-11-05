"""Separate immutable runtime provenance and same-release run pins; forward only."""

import json
from hashlib import sha256
from pathlib import Path

import sqlalchemy as sa
from alembic import op
from alembic.operations import Operations
from sqlalchemy.dialects import postgresql

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_runtime_20261105"
down_revision = "semantic_pce_foundation_20261105"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_runtime_20261105_native.json"
NATIVE_STATE_SHA256 = "a9354c4fd5975c8210ef1ea06e4b4372afa6ed4faa4a139c94d5b3b2cee65bd9"
NATIVE_ADMISSION_FILE = "semantic_runtime_20261105_admission.sql"
NATIVE_ADMISSION_SHA256 = "59b9e6a92d14ccb61bacdabfc1e6557fca9f35c10088493a6dc6382fcd40b384"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen runtime binding artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["predecessor"] != down_revision or state["version"] != 1:
        raise RuntimeError("incompatible runtime binding predecessor")
    _migration_role = op.get_bind().exec_driver_sql("SELECT current_user").scalar_one()
    op.create_table(
        "runtime_binding",
        sa.Column("release_id", sa.Text(), nullable=False),
        sa.Column("runtime_id", sa.Text(), nullable=False),
        sa.Column("manifest_bytes", postgresql.BYTEA(), nullable=False),
        sa.Column("archive_bytes", postgresql.BYTEA(), nullable=False),
        sa.ForeignKeyConstraint(
            ["release_id"], ["sem.release.release_id"], name=op.f("fk_runtime_binding_release_id")
        ),
        sa.PrimaryKeyConstraint("release_id", "runtime_id", name=op.f("pk_runtime_binding")),
        schema="sem",
        info={"model_class": "runtime_binding", "immutability": "intrinsic"},
    )
    op.add_column("run", sa.Column("runtime_id", sa.Text(), nullable=True), schema="ops")
    op.create_foreign_key(
        op.f("fk_run_release_id_runtime_id"),
        "run",
        "runtime_binding",
        ["release_id", "runtime_id"],
        ["release_id", "runtime_id"],
        source_schema="ops",
        referent_schema="sem",
    )
    op.execute("ALTER TABLE sem.runtime_binding OWNER TO corpus_sem_publisher")
    op.execute("SET LOCAL ROLE corpus_sem_publisher")
    op.execute(
        "INSERT INTO sem.physical_contract(physical_id,checks,source_digest) "
        "VALUES ('physical:3b8bf73266d764583aa8b31e50f57e471fe6155cd69f6c79a1"
        '1165c4c877b89b\',\'[{"expression": "(length(operation_version) > 0)", '
        '"name": "ck_alternative_group_physical_367a3f1b91", "relation": "dat'
        'a.alternative_group"}, {"expression": "(length(operation_id) > 0)", '
        '"name": "ck_alternative_group_physical_81a8ed4461", "relation": "dat'
        'a.alternative_group"}, {"expression": "((confidence IS NULL) OR ((co'
        'nfidence >= (0)::numeric) AND (confidence <= (1)::numeric)))", "name'
        '": "ck_assessment_physical_506af7cc40", "relation": "data.assessment'
        '"}, {"expression": "((fact_id IS NULL) <> (occurrence_id IS NULL))",'
        ' "name": "ck_assessment_physical_a44e2bbc14", "relation": "data.asse'
        'ssment"}, {"expression": "((counterpart_fact_id IS NULL) = (counterp'
        'art_occurrence_id IS NULL))", "name": "ck_assessment_physical_ba2418'
        'd4d2", "relation": "data.assessment"}, {"expression": "(data_revisio'
        'n > 0)", "name": "ck_batch_physical_239a1f5235", "relation": "data.b'
        "atch\"}, {\"expression\": \"(outcome = ANY (ARRAY[''complete''::text, ''"
        "partial''::text, ''unanalysed''::text, ''failed''::text]))\", \"name\":"
        ' "ck_coverage_physical_1a0a2904ca", "relation": "data.coverage"}, {"'
        'expression": "((source_outcome IS NULL) OR (outcome =\\nCASE\\n    WHE'
        "N (source_outcome = ANY (ARRAY[''unknown''::text, ''unsupported''::t"
        "ext])) THEN ''unanalysed''::text\\n    ELSE source_outcome\\nEND))\", \""
        'name": "ck_coverage_physical_76460b9b2b", "relation": "data.coverage'
        '"}, {"expression": "((source_outcome IS NULL) OR (source_outcome = A'
        "NY (ARRAY[''complete''::text, ''partial''::text, ''unknown''::text, "
        "''unsupported''::text, ''failed''::text])))\", \"name\": \"ck_coverage_p"
        'hysical_e6acac26e8", "relation": "data.coverage"}, {"expression": "('
        '\\"position\\" >= 0)", "name": "ck_derivation_premise_physical_9039b28'
        'f88", "relation": "data.derivation_premise"}, {"expression": "(reali'
        'zation_id <> input_realization_id)", "name": "ck_entity_input_physic'
        'al_c3379ef8c3", "relation": "data.entity_input"}, {"expression": "(i'
        'nput_data_revision >= 0)", "name": "ck_entity_input_physical_ed2a159'
        'c88", "relation": "data.entity_input"}, {"expression": "(basis = ANY'
        " (ARRAY[''declared_key''::text, ''global_label''::text, ''source_loc"
        'al\'\'::text]))", "name": "ck_entity_resolution_physical_1143a31dc3", '
        '"relation": "data.entity_resolution"}, {"expression": "(outcome = AN'
        "Y (ARRAY[''resolved''::text, ''ambiguous_anchor''::text, ''incomplet"
        "e_key''::text, ''ungrounded_cycle''::text]))\", \"name\": \"ck_entity_re"
        'solution_physical_4b568fb139", "relation": "data.entity_resolution"}'
        ', {"expression": "(((rendition_id IS NOT NULL) AND (source_view_id I'
        "S NULL) AND (native_address IS NULL)) OR ((rendition_id IS NULL) AND"
        " (span_id IS NULL) AND (source_view_id IS NOT NULL) AND (native_addr"
        'ess IS NOT NULL)))", "name": "ck_evidence_source_physical_0a487c0ebb'
        '", "relation": "data.evidence_source"}, {"expression": "(realization'
        '_id <> input_realization_id)", "name": "ck_fact_input_physical_c3379'
        'ef8c3", "relation": "data.fact_input"}, {"expression": "(input_data_'
        'revision >= 0)", "name": "ck_fact_input_physical_ed2a159c88", "relat'
        'ion": "data.fact_input"}, {"expression": "(left_kind = ANY (ARRAY[\'\''
        "local''::text, ''known''::text]))\", \"name\": \"ck_identity_exclusion_p"
        'hysical_5b61df693c", "relation": "data.identity_exclusion"}, {"expre'
        'ssion": "(left_entity_id <> right_entity_id)", "name": "ck_identity_'
        'exclusion_physical_b87f376563", "relation": "data.identity_exclusion'
        "\"}, {\"expression\": \"(right_kind = ANY (ARRAY[''local''::text, ''know"
        'n\'\'::text]))", "name": "ck_identity_exclusion_physical_f8edd6e4f3", '
        '"relation": "data.identity_exclusion"}, {"expression": "((statement_'
        'entity_id IS NOT NULL) OR (statement_role IS NOT NULL))", "name": "c'
        'k_occurrence_context_physical_e32eb26213", "relation": "data.occurre'
        'nce_context"}, {"expression": "(establishment = ANY (ARRAY[\'\'stated\''
        "'::text, ''derived''::text, ''agent_asserted''::text]))\", \"name\": \"c"
        'k_occurrence_establishment_physical_ef563c839f", "relation": "data.o'
        'ccurrence_establishment"}, {"expression": "(generation >= 0)", "name'
        '": "ck_project_physical_8313aadc77", "relation": "data.project"}, {"'
        'expression": "(source_revision >= 0)", "name": "ck_publication_inten'
        't_physical_0ed0eed26f", "relation": "data.publication_intent"}, {"ex'
        "pression\": \"((source_capture_id <> ''''::text) AND (operation_id <> "
        "''''::text) AND (projection_id <> ''''::text))\", \"name\": \"ck_publica"
        'tion_intent_physical_55ae0caf21", "relation": "data.publication_inte'
        "nt\"}, {\"expression\": \"(state = ANY (ARRAY[''active''::text, ''buildi"
        "ng''::text, ''retired''::text, ''failed''::text]))\", \"name\": \"ck_rea"
        'lization_physical_3a1078e1fe", "relation": "data.realization"}, {"ex'
        'pression": "(data_revision >= 0)", "name": "ck_realization_physical_'
        '8c71a80efa", "relation": "data.realization"}, {"expression": "(\\"pos'
        'ition\\" >= 0)", "name": "ck_record_alternative_physical_9039b28f88",'
        ' "relation": "data.record_alternative"}, {"expression": "(\\"position'
        '\\" >= 0)", "name": "ck_record_alternative_evidence_physical_9039b28f'
        '88", "relation": "data.record_alternative_evidence"}, {"expression":'
        ' "(\\"position\\" >= 0)", "name": "ck_record_alternative_piece_physica'
        'l_9039b28f88", "relation": "data.record_alternative_piece"}, {"expre'
        'ssion": "(\\"position\\" >= 0)", "name": "ck_record_anchor_physical_90'
        '39b28f88", "relation": "data.record_anchor"}, {"expression": "(\\"pos'
        'ition\\" >= 0)", "name": "ck_record_dependency_physical_9039b28f88", '
        '"relation": "data.record_dependency"}, {"expression": "(\\"position\\"'
        ' >= 0)", "name": "ck_record_evidence_member_physical_9039b28f88", "r'
        'elation": "data.record_evidence_member"}, {"expression": "(\\"positio'
        'n\\" >= 0)", "name": "ck_record_evidence_set_physical_9039b28f88", "r'
        'elation": "data.record_evidence_set"}, {"expression": "(\\"position\\"'
        ' >= 0)", "name": "ck_record_field_physical_9039b28f88", "relation": '
        '"data.record_field"}, {"expression": "(\\"position\\" >= 0)", "name": '
        '"ck_record_field_evidence_physical_9039b28f88", "relation": "data.re'
        'cord_field_evidence"}, {"expression": "(\\"position\\" >= 0)", "name":'
        ' "ck_record_field_piece_physical_9039b28f88", "relation": "data.reco'
        'rd_field_piece"}, {"expression": "(\\"position\\" >= 0)", "name": "ck_'
        'record_occurrence_anchor_physical_9039b28f88", "relation": "data.rec'
        'ord_occurrence_anchor"}, {"expression": "(\\"position\\" >= 0)", "name'
        '": "ck_record_premise_physical_9039b28f88", "relation": "data.record'
        '_premise"}, {"expression": "(\\"position\\" >= 0)", "name": "ck_record'
        '_private_assertion_physical_9039b28f88", "relation": "data.record_pr'
        'ivate_assertion"}, {"expression": "(\\"position\\" >= 0)", "name": "ck'
        '_record_report_member_physical_9039b28f88", "relation": "data.record'
        "_report_member\"}, {\"expression\": \"((kind <> ''integer''::text) OR (t"
        "ext_value ~ ''^[+-]?[0-9]+$''::text))\", \"name\": \"ck_typed_value_phys"
        'ical_053b27098a", "relation": "data.typed_value"}, {"expression": "\\'
        "nCASE\\n    WHEN (integer_value IS NULL) THEN true\\n    ELSE ((intege"
        "r_value = trunc(integer_value)) AND (integer_value = (text_value)::n"
        'umeric))\\nEND", "name": "ck_typed_value_physical_05579de47e", "relat'
        'ion": "data.typed_value"}, {"expression": "\\nCASE\\n    WHEN (numeric'
        "_value IS NULL) THEN true\\n    ELSE (numeric_value = (decimal_lexica"
        'l)::numeric)\\nEND", "name": "ck_typed_value_physical_1338461682", "r'
        'elation": "data.typed_value"}, {"expression": "((decimal_lexical IS '
        "NULL) OR (decimal_lexical ~ ''^[+-]?([0-9]+(\\\\.[0-9]*)?|\\\\.[0-9]+)(["
        'eE][+-]?[0-9]+)?$\'\'::text))", "name": "ck_typed_value_physical_6d983'
        '4e238", "relation": "data.typed_value"}, {"expression": "((numeric_v'
        "alue IS NULL) OR (kind = ANY (ARRAY[''decimal''::text, ''number''::t"
        'ext])))", "name": "ck_typed_value_physical_77f076c9cb", "relation": '
        '"data.typed_value"}, {"expression": "((integer_value IS NULL) OR (ki'
        "nd = ''integer''::text))\", \"name\": \"ck_typed_value_physical_b4572e9f"
        '51", "relation": "data.typed_value"}, {"expression": "(kind = ANY (A'
        "RRAY[''string''::text, ''integer''::text, ''decimal''::text, ''numbe"
        "r''::text, ''boolean''::text, ''entity''::text, ''null''::text, ''mi"
        "ssing''::text, ''sequence''::text, ''mapping''::text, ''record''::te"
        "xt, ''interval''::text, ''expression''::text, ''date''::text, ''date"
        "time''::text, ''float''::text, ''opaque''::text]))\", \"name\": \"ck_typ"
        'ed_value_physical_d01245fe40", "relation": "data.typed_value"}, {"ex'
        "pression\": \"(((kind = ANY (ARRAY[''string''::text, ''integer''::text"
        ", ''date''::text, ''datetime''::text, ''float''::text, ''expression'"
        "'::text, ''missing''::text])) AND (text_value IS NOT NULL) AND (deci"
        "mal_lexical IS NULL) AND (boolean_value IS NULL) AND (entity_id IS N"
        "ULL) AND (opaque_payload IS NULL)) OR ((kind = ANY (ARRAY[''decimal'"
        "'::text, ''number''::text])) AND (text_value IS NULL) AND (decimal_l"
        "exical IS NOT NULL) AND (boolean_value IS NULL) AND (entity_id IS NU"
        "LL) AND (opaque_payload IS NULL)) OR ((kind = ''boolean''::text) AND"
        " (text_value IS NULL) AND (decimal_lexical IS NULL) AND (boolean_val"
        "ue IS NOT NULL) AND (entity_id IS NULL) AND (opaque_payload IS NULL)"
        ") OR ((kind = ''entity''::text) AND (text_value IS NULL) AND (decima"
        "l_lexical IS NULL) AND (boolean_value IS NULL) AND (entity_id IS NOT"
        " NULL) AND (opaque_payload IS NULL)) OR ((kind = ''opaque''::text) A"
        "ND (text_value IS NULL) AND (decimal_lexical IS NULL) AND (boolean_v"
        "alue IS NULL) AND (entity_id IS NULL) AND (opaque_payload IS NOT NUL"
        "L)) OR ((kind = ANY (ARRAY[''null''::text, ''sequence''::text, ''map"
        "ping''::text, ''record''::text, ''interval''::text])) AND (text_valu"
        "e IS NULL) AND (decimal_lexical IS NULL) AND (boolean_value IS NULL)"
        ' AND (entity_id IS NULL) AND (opaque_payload IS NULL)))", "name": "c'
        'k_typed_value_physical_dcfa9b38a9", "relation": "data.typed_value"},'
        ' {"expression": "(\\"position\\" >= 0)", "name": "ck_value_role_physic'
        'al_9039b28f88", "relation": "data.value_role"}, {"expression": "(spl'
        "it = ANY (ARRAY[''dev''::text, ''test''::text, ''reserved''::text]))"
        '", "name": "ck_document_split_physical_a319d8e82e", "relation": "eva'
        'l.document_split"}, {"expression": "(((rendition_id IS NOT NULL) AND'
        " (source_view_id IS NULL) AND (projection_digest IS NULL)) OR ((rend"
        "ition_id IS NULL) AND (source_view_id IS NOT NULL) AND (projection_d"
        'igest IS NOT NULL)))", "name": "ck_reference_frame_physical_01217a18'
        'f9", "relation": "eval.reference_frame"}, {"expression": "(version >'
        ' 0)", "name": "ck_reference_frame_physical_429634fbaa", "relation": '
        '"eval.reference_frame"}, {"expression": "(partition = ANY (ARRAY[\'\'d'
        "evelopment''::text, ''feature_fit''::text, ''final_event_calibration"
        "''::text, ''final_assessment''::text]))\", \"name\": \"ck_reference_orig"
        'in_group_physical_93d7ebbb1a", "relation": "eval.reference_origin_gr'
        'oup"}, {"expression": "(origin_group <> \'\'\'\'::text)", "name": "ck_re'
        'ference_origin_group_physical_e496f41f44", "relation": "eval.referen'
        'ce_origin_group"}, {"expression": "((jsonb_typeof(provenance) = \'\'ob'
        "ject''::text) AND (provenance <> ''{}''::jsonb))\", \"name\": \"ck_refer"
        'ence_origin_group_physical_e953a56fc9", "relation": "eval.reference_'
        "origin_group\"}, {\"expression\": \"(pass_kind = ANY (ARRAY[''A''::text,"
        " ''B''::text, ''C''::text]))\", \"name\": \"ck_reference_pass_physical_7"
        '182d42311", "relation": "eval.reference_pass"}, {"expression": "(spl'
        "it = ANY (ARRAY[''dev''::text, ''test''::text]))\", \"name\": \"ck_refer"
        'ence_set_physical_23de252598", "relation": "eval.reference_set"}, {"'
        'expression": "(((rendition_id IS NOT NULL) AND (source_view_id IS NU'
        "LL) AND (projection_digest IS NULL)) OR ((rendition_id IS NULL) AND "
        '(source_view_id IS NOT NULL) AND (projection_digest IS NOT NULL)))",'
        ' "name": "ck_reference_unit_physical_01217a18f9", "relation": "eval.'
        'reference_unit"}, {"expression": "(ordinal >= 0)", "name": "ck_obser'
        'vation_physical_ee668cd4ef", "relation": "kb.observation"}, {"expres'
        'sion": "(role <> \'\'\'\'::text)", "name": "ck_observation_input_physica'
        'l_08d176bdbd", "relation": "kb.observation_input"}, {"expression": "'
        '(\\"position\\" >= 0)", "name": "ck_observation_input_physical_9039b28'
        'f88", "relation": "kb.observation_input"}, {"expression": "(input_in'
        'dex >= 0)", "name": "ck_pdf_mapping_report_physical_61d721fcae", "re'
        'lation": "kb.pdf_mapping_report"}, {"expression": "(report_index >= '
        '0)", "name": "ck_pdf_mapping_report_physical_9c8bca1fd0", "relation"'
        ': "kb.pdf_mapping_report"}, {"expression": "(kind = ANY (ARRAY[\'\'ite'
        "m''::text, ''cell''::text, ''formula''::text, ''chart''::text, ''tex"
        "t''::text, ''region''::text]))\", \"name\": \"ck_pdf_occurrence_physical"
        '_367474e9a3", "relation": "kb.pdf_occurrence"}, {"expression": "(NOT'
        " (pointer IS DISTINCT FROM (body ->> ''pointer''::text)))\", \"name\": "
        '"ck_pdf_occurrence_physical_4c3854096c", "relation": "kb.pdf_occurre'
        'nce"}, {"expression": "(\\"precision\\" = ANY (ARRAY[\'\'unknown\'\'::text'
        ", ''coarse''::text, ''inherited''::text, ''block''::text, ''item''::"
        "text, ''cell''::text, ''word''::text, ''glyph''::text]))\", \"name\": \""
        'ck_pdf_occurrence_physical_77605f0884", "relation": "kb.pdf_occurren'
        'ce"}, {"expression": "(occurrence_id <> \'\'\'\'::text)", "name": "ck_pd'
        'f_occurrence_physical_ec6f050edd", "relation": "kb.pdf_occurrence"},'
        ' {"expression": "(coverage_id <> \'\'\'\'::text)", "name": "ck_pdf_produ'
        'ct_coverage_physical_93d06b5b0d", "relation": "kb.pdf_product_covera'
        "ge\"}, {\"expression\": \"(family = ANY (ARRAY[''coverage''::text, ''hea"
        "lth''::text, ''input''::text, ''mapping_report''::text, ''native_met"
        "adata''::text, ''occurrence''::text, ''relation''::text, ''request_o"
        'utcome\'\'::text]))", "name": "ck_pdf_record_companion_family_a1f36c0d'
        '0c", "relation": "kb.pdf_record_companion"}, {"expression": "(produc'
        't_id = revision_id)", "name": "ck_pdf_record_companion_physical_a185'
        '59f6de", "relation": "kb.pdf_record_companion"}, {"expression": "(js'
        "onb_typeof(body) = ''object''::text)\", \"name\": \"ck_pdf_record_compan"
        'ion_physical_c92e13f700", "relation": "kb.pdf_record_companion"}, {"'
        'expression": "(octet_length((body)::text) <= 65536)", "name": "ck_pd'
        'f_record_companion_physical_fb42f25a72", "relation": "kb.pdf_record_'
        "companion\"}, {\"expression\": \"(family = ANY (ARRAY[''coverage''::text"
        ", ''health''::text, ''input''::text, ''mapping_report''::text, ''nat"
        "ive_metadata''::text, ''occurrence''::text, ''relation''::text, ''re"
        'quest_outcome\'\'::text]))", "name": "ck_pdf_record_companion_field_fa'
        'mily_a1f36c0d0c", "relation": "kb.pdf_record_companion_field"}, {"ex'
        "pression\": \"(field_name = ANY (ARRAY[''text''::text, ''value''::text"
        ']))", "name": "ck_pdf_record_companion_field_field_name_50e2349d3e",'
        ' "relation": "kb.pdf_record_companion_field"}, {"expression": "(((fa'
        "mily = ''native_metadata''::text) AND (field_name = ''value''::text)"
        " AND (scalar_kind = ''y''::text)) OR ((family = ''occurrence''::text"
        ") AND (field_name = ''text''::text) AND (scalar_kind = ''s''::text))"
        ')", "name": "ck_pdf_record_companion_field_physical_795eae16ab", "re'
        'lation": "kb.pdf_record_companion_field"}, {"expression": "(product_'
        'id = revision_id)", "name": "ck_pdf_record_companion_field_physical_'
        'a18559f6de", "relation": "kb.pdf_record_companion_field"}, {"express'
        "ion\": \"(scalar_kind = ANY (ARRAY[''s''::text, ''y''::text]))\", \"name"
        '": "ck_pdf_record_companion_field_scalar_kind_775eba9be0", "relation'
        '": "kb.pdf_record_companion_field"}, {"expression": "(product_id = r'
        'evision_id)", "name": "ck_pdf_record_endpoint_physical_a18559f6de", '
        '"relation": "kb.pdf_record_endpoint"}, {"expression": "(ordinal >= 0'
        ')", "name": "ck_pdf_record_endpoint_physical_ee668cd4ef", "relation"'
        ': "kb.pdf_record_endpoint"}, {"expression": "(ordinal >= 0)", "name"'
        ': "ck_pdf_record_membership_ordinal_ee668cd4ef", "relation": "kb.pdf'
        "_record_membership\"}, {\"expression\": \"((value_kind = ''scalar''::tex"
        't) OR (scalar_json IS NULL))", "name": "ck_pdf_record_membership_phy'
        'sical_341b42c0f9", "relation": "kb.pdf_record_membership"}, {"expres'
        "sion\": \"((value_kind = ''record''::text) = (record_id IS NOT NULL))\""
        ', "name": "ck_pdf_record_membership_physical_8028c34622", "relation"'
        ': "kb.pdf_record_membership"}, {"expression": "((member_key IS NULL)'
        ' OR (member_key_stream_id IS NULL))", "name": "ck_pdf_record_members'
        'hip_physical_8bf5b8b4d7", "relation": "kb.pdf_record_membership"}, {'
        "\"expression\": \"(octet_length(convert_to((scalar_json)::text, ''UTF8'"
        '\'::name)) <= 65536)", "name": "ck_pdf_record_membership_physical_b66'
        'e6eb309", "relation": "kb.pdf_record_membership"}, {"expression": "('
        "(value_kind = ''parts''::text) = (stream_id IS NOT NULL))\", \"name\": "
        '"ck_pdf_record_membership_physical_df9d6518cd", "relation": "kb.pdf_'
        'record_membership"}, {"expression": "(value_kind = ANY (ARRAY[\'\'part'
        "s''::text, ''record''::text, ''scalar''::text]))\", \"name\": \"ck_pdf_r"
        'ecord_membership_value_kind_1ee79cbd9a", "relation": "kb.pdf_record_'
        "membership\"}, {\"expression\": \"(family = ANY (ARRAY[''cell''::text, '"
        "'detail''::text, ''header''::text, ''node''::text, ''page''::text, '"
        "'provenance''::text, ''reference''::text, ''table''::text]))\", \"name"
        '": "ck_pdf_record_native_family_896b469851", "relation": "kb.pdf_rec'
        'ord_native"}, {"expression": "(native_type <> \'\'\'\'::text)", "name": '
        '"ck_pdf_record_native_physical_1e27d9c8ce", "relation": "kb.pdf_reco'
        'rd_native"}, {"expression": "(jsonb_typeof(structure_json) = \'\'objec'
        't\'\'::text)", "name": "ck_pdf_record_native_physical_39016badae", "re'
        'lation": "kb.pdf_record_native"}, {"expression": "((native_address I'
        'S NULL) <> (native_address_stream_id IS NULL))", "name": "ck_pdf_rec'
        'ord_native_physical_4c7b8c414a", "relation": "kb.pdf_record_native"}'
        ", {\"expression\": \"(jsonb_typeof(scalars_json) = ''object''::text)\", "
        '"name": "ck_pdf_record_native_physical_af247a6f3c", "relation": "kb.'
        'pdf_record_native"}, {"expression": "(octet_length(convert_to((struc'
        "ture_json)::text, ''UTF8''::name)) <= 65536)\", \"name\": \"ck_pdf_recor"
        'd_native_physical_c09752f060", "relation": "kb.pdf_record_native"}, '
        '{"expression": "(octet_length(convert_to((scalars_json)::text, \'\'UTF'
        '8\'\'::name)) <= 65536)", "name": "ck_pdf_record_native_physical_c4ce4'
        'd92f6", "relation": "kb.pdf_record_native"}, {"expression": "(record'
        "_id <> ''''::text)\", \"name\": \"ck_pdf_record_native_physical_d10d461f"
        '9b", "relation": "kb.pdf_record_native"}, {"expression": "((native_p'
        'ointer IS NULL) <> (native_pointer_stream_id IS NULL))", "name": "ck'
        '_pdf_record_reference_physical_15d32f6137", "relation": "kb.pdf_reco'
        'rd_reference"}, {"expression": "(((field_name = ANY (ARRAY[\'\'source_'
        "cell_id''::text, ''target_cell_id''::text])) AND (native_pointer ~ '"
        "'^-?[0-9]+$''::text)) OR ((field_name <> ALL (ARRAY[''source_cell_id"
        "''::text, ''target_cell_id''::text])) AND (native_pointer ~~ ''#%'':"
        ':text)))", "name": "ck_pdf_record_reference_physical_84ee799da6", "r'
        'elation": "kb.pdf_record_reference"}, {"expression": "(reference_id '
        "<> ''''::text)\", \"name\": \"ck_pdf_record_reference_physical_b4d49caa5"
        'd", "relation": "kb.pdf_record_reference"}, {"expression": "(relatio'
        'n_id <> \'\'\'\'::text)", "name": "ck_pdf_relation_physical_58def7fcc7",'
        ' "relation": "kb.pdf_relation"}, {"expression": "(kind = ANY (ARRAY['
        "''correspondence''::text, ''decision''::text]))\", \"name\": \"ck_pdf_re"
        'lation_physical_fa34f4062b", "relation": "kb.pdf_relation"}, {"expre'
        'ssion": "(endpoint_index >= 0)", "name": "ck_pdf_relation_endpoint_p'
        'hysical_379ac917ae", "relation": "kb.pdf_relation_endpoint"}, {"expr'
        "ession\": \"(role = ANY (ARRAY[''input''::text, ''output''::text, ''al"
        "ternative''::text, ''evidence''::text]))\", \"name\": \"ck_pdf_relation_"
        'endpoint_physical_41bc0f1575", "relation": "kb.pdf_relation_endpoint'
        '"}, {"expression": "(artifact_digest = encode(sha256(content), \'\'hex'
        '\'\'::text))", "name": "ck_source_artifact_physical_b9e3edc5d9", "rela'
        'tion": "kb.source_artifact"}, {"expression": "(key <> \'\'\'\'::text)", '
        '"name": "ck_source_view_physical_1d77c7a418", "relation": "kb.source'
        '_view"}, {"expression": "(native_build_id = native_revision_id)", "n'
        'ame": "ck_source_view_physical_73dfcc4ba8", "relation": "kb.source_v'
        "iew\"}, {\"expression\": \"(membership = ANY (ARRAY[''direct''::text, ''"
        'descendants\'\'::text]))", "name": "ck_source_view_physical_e3320d3f8a'
        '", "relation": "kb.source_view"}, {"expression": "((source_position '
        'IS NULL) OR (source_position >= 0))", "name": "ck_measurement_physic'
        'al_a0486ccc73", "relation": "ops.measurement"}, {"expression": "((co'
        "nfiguration_schema_digest IS NULL) OR (configuration_schema_digest ~"
        " ''^[0-9a-f]{64}$''::text))\", \"name\": \"ck_method_physical_95ee0996a8"
        '", "relation": "ops.method"}, {"expression": "(native_build_id = nat'
        'ive_revision_id)", "name": "ck_native_region_artifact_physical_73dfc'
        'c4ba8", "relation": "ops.native_region_artifact"}, {"expression": "('
        'end_offset > start_offset)", "name": "ck_native_source_frame_sentenc'
        'e_physical_01f330ec6a", "relation": "ops.native_source_frame_sentenc'
        'e"}, {"expression": "(start_offset >= 0)", "name": "ck_native_source'
        '_frame_sentence_physical_43e7c4875a", "relation": "ops.native_source'
        '_frame_sentence"}, {"expression": "(membership = ANY (ARRAY[\'\'direct'
        "''::text, ''descendants''::text]))\", \"name\": \"ck_native_source_frame"
        '_source_physical_6fc6fa39d4", "relation": "ops.native_source_frame_s'
        "ource\"}, {\"expression\": \"(role = ANY (ARRAY[''primary''::text, ''anc"
        'estor_context\'\'::text]))", "name": "ck_native_source_frame_source_ph'
        'ysical_c2fa28fa87", "relation": "ops.native_source_frame_source"}, {'
        '"expression": "(byte_length >= 0)", "name": "ck_pdf_artifact_part_by'
        'te_length_0392ce7ab3", "relation": "ops.pdf_artifact_part"}, {"expre'
        'ssion": "(byte_offset >= 0)", "name": "ck_pdf_artifact_part_byte_off'
        'set_5dc7051d0c", "relation": "ops.pdf_artifact_part"}, {"expression"'
        ': "(ordinal >= 0)", "name": "ck_pdf_artifact_part_ordinal_ee668cd4ef'
        '", "relation": "ops.pdf_artifact_part"}, {"expression": "(sha256_dig'
        "est = encode(sha256(body), ''hex''::text))\", \"name\": \"ck_pdf_artifac"
        't_part_physical_266e3bac59", "relation": "ops.pdf_artifact_part"}, {'
        '"expression": "(byte_length <= 65536)", "name": "ck_pdf_artifact_par'
        't_physical_3bbd16db25", "relation": "ops.pdf_artifact_part"}, {"expr'
        'ession": "(byte_length = octet_length(body))", "name": "ck_pdf_artif'
        'act_part_physical_9cde4d345e", "relation": "ops.pdf_artifact_part"},'
        ' {"expression": "(byte_length > 0)", "name": "ck_pdf_artifact_part_p'
        'hysical_f369db0b22", "relation": "ops.pdf_artifact_part"}, {"express'
        'ion": "(byte_length >= 0)", "name": "ck_pdf_artifact_stream_byte_len'
        'gth_0392ce7ab3", "relation": "ops.pdf_artifact_stream"}, {"expressio'
        'n": "(serialization_sha256 ~ \'\'^[0-9a-f]{64}$\'\'::text)", "name": "ck'
        '_pdf_artifact_stream_physical_353c63835f", "relation": "ops.pdf_arti'
        'fact_stream"}, {"expression": "(encoding_profile <> \'\'\'\'::text)", "n'
        'ame": "ck_pdf_artifact_stream_physical_66ee4db5f7", "relation": "ops'
        '.pdf_artifact_stream"}, {"expression": "(byte_root ~ \'\'^[0-9a-f]{64}'
        '$\'\'::text)", "name": "ck_pdf_artifact_stream_physical_860f4eb238", "'
        'relation": "ops.pdf_artifact_stream"}, {"expression": "(stream_id <>'
        ' \'\'\'\'::text)", "name": "ck_pdf_artifact_stream_physical_94d0a9f5c9",'
        ' "relation": "ops.pdf_artifact_stream"}, {"expression": "(kind = ANY'
        " (ARRAY[''integrated''::text, ''native''::text]))\", \"name\": \"ck_pdf_"
        'frozen_build_kind_41bc3f952e", "relation": "ops.pdf_frozen_build"}, '
        "{\"expression\": \"(kind = ANY (ARRAY[''native''::text, ''recognition_o"
        "bservation''::text, ''integrated''::text]))\", \"name\": \"ck_pdf_produc"
        't_physical_2b69fdd7c7", "relation": "ops.pdf_product"}, {"expression'
        '": "(contract_digest ~ \'\'^[0-9a-f]{64}$\'\'::text)", "name": "ck_pdf_p'
        'roduct_physical_361bb11ec1", "relation": "ops.pdf_product"}, {"expre'
        'ssion": "(product_key <> \'\'\'\'::text)", "name": "ck_pdf_product_physi'
        'cal_37bf79141e", "relation": "ops.pdf_product"}, {"expression": "(co'
        "ntent_digest ~ ''^[0-9a-f]{64}$''::text)\", \"name\": \"ck_pdf_product_p"
        'hysical_6452181ff1", "relation": "ops.pdf_product"}, {"expression": '
        '"(descriptor = ops.pdf_product_descriptor(payload))", "name": "ck_pd'
        'f_product_body_physical_acbf4a8f01", "relation": "ops.pdf_product_bo'
        'dy"}, {"expression": "((task_id <> input_task_id) OR (product_key <>'
        ' input_product_key))", "name": "ck_pdf_product_input_physical_6108dd'
        'ec8c", "relation": "ops.pdf_product_input"}, {"expression": "(input_'
        'index >= 0)", "name": "ck_pdf_product_input_physical_61d721fcae", "r'
        'elation": "ops.pdf_product_input"}, {"expression": "(role = ANY (ARR'
        "AY[''structural''::text, ''recognition''::text, ''alternative''::tex"
        "t, ''policy_input''::text]))\", \"name\": \"ck_pdf_product_input_physica"
        'l_afd3c389de", "relation": "ops.pdf_product_input"}, {"expression": '
        "\"(kind = ANY (ARRAY[''integrated''::text, ''native''::text]))\", \"nam"
        'e": "ck_pdf_published_revision_kind_41bc3f952e", "relation": "ops.pd'
        'f_published_revision"}, {"expression": "(contract_version = \'\'pdf-na'
        'tive-records-v1\'\'::text)", "name": "ck_pdf_record_document_contract_'
        'version_47929bf068", "relation": "ops.pdf_record_document"}, {"expre'
        "ssion\": \"(mapping_profile = ''pdf-native-records-v1''::text)\", \"name"
        '": "ck_pdf_record_document_mapping_profile_e3d5e39c85", "relation": '
        '"ops.pdf_record_document"}, {"expression": "(product_id <> \'\'\'\'::tex'
        't)", "name": "ck_pdf_record_document_physical_1246cec1c1", "relation'
        '": "ops.pdf_record_document"}, {"expression": "(source_digest ~ \'\'^['
        '0-9a-f]{64}$\'\'::text)", "name": "ck_pdf_record_document_physical_1b3'
        '2a362eb", "relation": "ops.pdf_record_document"}, {"expression": "(n'
        "ative_schema_digest ~ ''^[0-9a-f]{64}$''::text)\", \"name\": \"ck_pdf_re"
        'cord_document_physical_26e3a40d89", "relation": "ops.pdf_record_docu'
        'ment"}, {"expression": "(revision_id <> \'\'\'\'::text)", "name": "ck_pd'
        'f_record_document_physical_b85b787d88", "relation": "ops.pdf_record_'
        'document"}, {"expression": "(byte_length >= 0)", "name": "ck_pdf_sta'
        'ge_artifact_part_byte_length_0392ce7ab3", "relation": "ops.pdf_stage'
        '_artifact_part"}, {"expression": "(byte_offset >= 0)", "name": "ck_p'
        'df_stage_artifact_part_byte_offset_5dc7051d0c", "relation": "ops.pdf'
        '_stage_artifact_part"}, {"expression": "(ordinal >= 0)", "name": "ck'
        '_pdf_stage_artifact_part_ordinal_ee668cd4ef", "relation": "ops.pdf_s'
        'tage_artifact_part"}, {"expression": "(sha256_digest = encode(sha256'
        "(body), ''hex''::text))\", \"name\": \"ck_pdf_stage_artifact_part_physic"
        'al_266e3bac59", "relation": "ops.pdf_stage_artifact_part"}, {"expres'
        'sion": "(byte_length <= 65536)", "name": "ck_pdf_stage_artifact_part'
        '_physical_3bbd16db25", "relation": "ops.pdf_stage_artifact_part"}, {'
        '"expression": "(byte_length = octet_length(body))", "name": "ck_pdf_'
        'stage_artifact_part_physical_9cde4d345e", "relation": "ops.pdf_stage'
        '_artifact_part"}, {"expression": "(product_id = revision_id)", "name'
        '": "ck_pdf_stage_artifact_part_physical_a18559f6de", "relation": "op'
        's.pdf_stage_artifact_part"}, {"expression": "(byte_length > 0)", "na'
        'me": "ck_pdf_stage_artifact_part_physical_f369db0b22", "relation": "'
        'ops.pdf_stage_artifact_part"}, {"expression": "(byte_length >= 0)", '
        '"name": "ck_pdf_stage_artifact_stream_byte_length_0392ce7ab3", "rela'
        'tion": "ops.pdf_stage_artifact_stream"}, {"expression": "(serializat'
        "ion_sha256 ~ ''^[0-9a-f]{64}$''::text)\", \"name\": \"ck_pdf_stage_artif"
        'act_stream_physical_353c63835f", "relation": "ops.pdf_stage_artifact'
        '_stream"}, {"expression": "(encoding_profile <> \'\'\'\'::text)", "name"'
        ': "ck_pdf_stage_artifact_stream_physical_66ee4db5f7", "relation": "o'
        'ps.pdf_stage_artifact_stream"}, {"expression": "(byte_root ~ \'\'^[0-9'
        'a-f]{64}$\'\'::text)", "name": "ck_pdf_stage_artifact_stream_physical_'
        '860f4eb238", "relation": "ops.pdf_stage_artifact_stream"}, {"express'
        'ion": "(stream_id <> \'\'\'\'::text)", "name": "ck_pdf_stage_artifact_st'
        'ream_physical_94d0a9f5c9", "relation": "ops.pdf_stage_artifact_strea'
        'm"}, {"expression": "(product_id = revision_id)", "name": "ck_pdf_st'
        'age_artifact_stream_physical_a18559f6de", "relation": "ops.pdf_stage'
        '_artifact_stream"}, {"expression": "(attempt > 0)", "name": "ck_pdf_'
        'stage_build_physical_0c8a59b69d", "relation": "ops.pdf_stage_build"}'
        ', {"expression": "(source_digest ~ \'\'^[0-9a-f]{64}$\'\'::text)", "name'
        '": "ck_pdf_stage_build_physical_1b32a362eb", "relation": "ops.pdf_st'
        "age_build\"}, {\"expression\": \"(recipe_digest ~ ''^[0-9a-f]{64}$''::te"
        'xt)", "name": "ck_pdf_stage_build_physical_3058c3002b", "relation": '
        '"ops.pdf_stage_build"}, {"expression": "(schema_digest ~ \'\'^[0-9a-f]'
        '{64}$\'\'::text)", "name": "ck_pdf_stage_build_physical_6416099f87", "'
        'relation": "ops.pdf_stage_build"}, {"expression": "(build_id <> \'\'\'\''
        '::text)", "name": "ck_pdf_stage_build_physical_8147daae94", "relatio'
        'n": "ops.pdf_stage_build"}, {"expression": "(state = ANY (ARRAY[\'\'ab'
        "andoned''::text, ''frozen''::text, ''open''::text, ''published''::te"
        'xt]))", "name": "ck_pdf_stage_build_state_8d8dc4ae4a", "relation": "'
        'ops.pdf_stage_build"}, {"expression": "(family = ANY (ARRAY[\'\'covera'
        "ge''::text, ''health''::text, ''input''::text, ''mapping_report''::t"
        "ext, ''native_metadata''::text, ''occurrence''::text, ''relation''::"
        "text, ''request_outcome''::text]))\", \"name\": \"ck_pdf_stage_companion"
        '_family_a1f36c0d0c", "relation": "ops.pdf_stage_companion"}, {"expre'
        'ssion": "(product_id = revision_id)", "name": "ck_pdf_stage_companio'
        'n_physical_a18559f6de", "relation": "ops.pdf_stage_companion"}, {"ex'
        'pression": "(jsonb_typeof(body) = \'\'object\'\'::text)", "name": "ck_pd'
        'f_stage_companion_physical_c92e13f700", "relation": "ops.pdf_stage_c'
        'ompanion"}, {"expression": "(octet_length((body)::text) <= 65536)", '
        '"name": "ck_pdf_stage_companion_physical_fb42f25a72", "relation": "o'
        'ps.pdf_stage_companion"}, {"expression": "(family = ANY (ARRAY[\'\'cov'
        "erage''::text, ''health''::text, ''input''::text, ''mapping_report''"
        "::text, ''native_metadata''::text, ''occurrence''::text, ''relation'"
        "'::text, ''request_outcome''::text]))\", \"name\": \"ck_pdf_stage_compan"
        'ion_field_family_a1f36c0d0c", "relation": "ops.pdf_stage_companion_f'
        "ield\"}, {\"expression\": \"(field_name = ANY (ARRAY[''text''::text, ''v"
        'alue\'\'::text]))", "name": "ck_pdf_stage_companion_field_field_name_5'
        '0e2349d3e", "relation": "ops.pdf_stage_companion_field"}, {"expressi'
        "on\": \"(((family = ''native_metadata''::text) AND (field_name = ''val"
        "ue''::text) AND (scalar_kind = ''y''::text)) OR ((family = ''occurre"
        "nce''::text) AND (field_name = ''text''::text) AND (scalar_kind = ''"
        's\'\'::text)))", "name": "ck_pdf_stage_companion_field_physical_795eae'
        '16ab", "relation": "ops.pdf_stage_companion_field"}, {"expression": '
        '"(product_id = revision_id)", "name": "ck_pdf_stage_companion_field_'
        'physical_a18559f6de", "relation": "ops.pdf_stage_companion_field"}, '
        "{\"expression\": \"(scalar_kind = ANY (ARRAY[''s''::text, ''y''::text])"
        ')", "name": "ck_pdf_stage_companion_field_scalar_kind_775eba9be0", "'
        'relation": "ops.pdf_stage_companion_field"}, {"expression": "(contra'
        "ct_version = ''pdf-native-records-v1''::text)\", \"name\": \"ck_pdf_stag"
        'e_document_contract_version_47929bf068", "relation": "ops.pdf_stage_'
        'document"}, {"expression": "(mapping_profile = \'\'pdf-native-records-'
        'v1\'\'::text)", "name": "ck_pdf_stage_document_mapping_profile_e3d5e39'
        'c85", "relation": "ops.pdf_stage_document"}, {"expression": "(produc'
        "t_id <> ''''::text)\", \"name\": \"ck_pdf_stage_document_physical_1246ce"
        'c1c1", "relation": "ops.pdf_stage_document"}, {"expression": "(sourc'
        "e_digest ~ ''^[0-9a-f]{64}$''::text)\", \"name\": \"ck_pdf_stage_documen"
        't_physical_1b32a362eb", "relation": "ops.pdf_stage_document"}, {"exp'
        "ression\": \"(native_schema_digest ~ ''^[0-9a-f]{64}$''::text)\", \"name"
        '": "ck_pdf_stage_document_physical_26e3a40d89", "relation": "ops.pdf'
        '_stage_document"}, {"expression": "(product_id = revision_id)", "nam'
        'e": "ck_pdf_stage_document_physical_a18559f6de", "relation": "ops.pd'
        'f_stage_document"}, {"expression": "(revision_id <> \'\'\'\'::text)", "n'
        'ame": "ck_pdf_stage_document_physical_b85b787d88", "relation": "ops.'
        'pdf_stage_document"}, {"expression": "(product_id = revision_id)", "'
        'name": "ck_pdf_stage_endpoint_physical_a18559f6de", "relation": "ops'
        '.pdf_stage_endpoint"}, {"expression": "(ordinal >= 0)", "name": "ck_'
        'pdf_stage_endpoint_physical_ee668cd4ef", "relation": "ops.pdf_stage_'
        'endpoint"}, {"expression": "(ordinal >= 0)", "name": "ck_pdf_stage_m'
        'embership_ordinal_ee668cd4ef", "relation": "ops.pdf_stage_membership'
        "\"}, {\"expression\": \"((value_kind = ''scalar''::text) OR (scalar_json"
        ' IS NULL))", "name": "ck_pdf_stage_membership_physical_341b42c0f9", '
        '"relation": "ops.pdf_stage_membership"}, {"expression": "((value_kin'
        "d = ''record''::text) = (record_id IS NOT NULL))\", \"name\": \"ck_pdf_s"
        'tage_membership_physical_8028c34622", "relation": "ops.pdf_stage_mem'
        'bership"}, {"expression": "((member_key IS NULL) OR (member_key_stre'
        'am_id IS NULL))", "name": "ck_pdf_stage_membership_physical_8bf5b8b4'
        'd7", "relation": "ops.pdf_stage_membership"}, {"expression": "(produ'
        'ct_id = revision_id)", "name": "ck_pdf_stage_membership_physical_a18'
        '559f6de", "relation": "ops.pdf_stage_membership"}, {"expression": "('
        "octet_length(convert_to((scalar_json)::text, ''UTF8''::name)) <= 655"
        '36)", "name": "ck_pdf_stage_membership_physical_b66e6eb309", "relati'
        'on": "ops.pdf_stage_membership"}, {"expression": "((value_kind = \'\'p'
        'arts\'\'::text) = (stream_id IS NOT NULL))", "name": "ck_pdf_stage_mem'
        'bership_physical_df9d6518cd", "relation": "ops.pdf_stage_membership"'
        "}, {\"expression\": \"(value_kind = ANY (ARRAY[''parts''::text, ''recor"
        "d''::text, ''scalar''::text]))\", \"name\": \"ck_pdf_stage_membership_va"
        'lue_kind_1ee79cbd9a", "relation": "ops.pdf_stage_membership"}, {"exp'
        "ression\": \"(family = ANY (ARRAY[''cell''::text, ''detail''::text, ''"
        "header''::text, ''node''::text, ''page''::text, ''provenance''::text"
        ", ''reference''::text, ''table''::text]))\", \"name\": \"ck_pdf_stage_na"
        'tive_family_896b469851", "relation": "ops.pdf_stage_native"}, {"expr'
        'ession": "(native_type <> \'\'\'\'::text)", "name": "ck_pdf_stage_native'
        '_physical_1e27d9c8ce", "relation": "ops.pdf_stage_native"}, {"expres'
        'sion": "(jsonb_typeof(structure_json) = \'\'object\'\'::text)", "name": '
        '"ck_pdf_stage_native_physical_39016badae", "relation": "ops.pdf_stag'
        'e_native"}, {"expression": "((native_address IS NULL) <> (native_add'
        'ress_stream_id IS NULL))", "name": "ck_pdf_stage_native_physical_4c7'
        'b8c414a", "relation": "ops.pdf_stage_native"}, {"expression": "(prod'
        'uct_id = revision_id)", "name": "ck_pdf_stage_native_physical_a18559'
        'f6de", "relation": "ops.pdf_stage_native"}, {"expression": "(jsonb_t'
        "ypeof(scalars_json) = ''object''::text)\", \"name\": \"ck_pdf_stage_nati"
        've_physical_af247a6f3c", "relation": "ops.pdf_stage_native"}, {"expr'
        "ession\": \"(octet_length(convert_to((structure_json)::text, ''UTF8'':"
        ':name)) <= 65536)", "name": "ck_pdf_stage_native_physical_c09752f060'
        '", "relation": "ops.pdf_stage_native"}, {"expression": "(octet_lengt'
        "h(convert_to((scalars_json)::text, ''UTF8''::name)) <= 65536)\", \"nam"
        'e": "ck_pdf_stage_native_physical_c4ce4d92f6", "relation": "ops.pdf_'
        'stage_native"}, {"expression": "(record_id <> \'\'\'\'::text)", "name": '
        '"ck_pdf_stage_native_physical_d10d461f9b", "relation": "ops.pdf_stag'
        'e_native"}, {"expression": "(row_count >= 0)", "name": "ck_pdf_stage'
        '_receipt_row_count_dd30421036", "relation": "ops.pdf_stage_receipt"}'
        ', {"expression": "((native_pointer IS NULL) <> (native_pointer_strea'
        'm_id IS NULL))", "name": "ck_pdf_stage_reference_physical_15d32f6137'
        '", "relation": "ops.pdf_stage_reference"}, {"expression": "(((field_'
        "name = ANY (ARRAY[''source_cell_id''::text, ''target_cell_id''::text"
        "])) AND (native_pointer ~ ''^-?[0-9]+$''::text)) OR ((field_name <> "
        "ALL (ARRAY[''source_cell_id''::text, ''target_cell_id''::text])) AND"
        " (native_pointer ~~ ''#%''::text)))\", \"name\": \"ck_pdf_stage_referenc"
        'e_physical_84ee799da6", "relation": "ops.pdf_stage_reference"}, {"ex'
        'pression": "(product_id = revision_id)", "name": "ck_pdf_stage_refer'
        'ence_physical_a18559f6de", "relation": "ops.pdf_stage_reference"}, {'
        '"expression": "(reference_id <> \'\'\'\'::text)", "name": "ck_pdf_stage_'
        'reference_physical_b4d49caa5d", "relation": "ops.pdf_stage_reference'
        "\"}, {\"expression\": \"(status = ANY (ARRAY[''created''::text, ''runnin"
        "g''::text, ''consolidating''::text, ''finished''::text, ''failed''::"
        'text, \'\'cancelled\'\'::text]))", "name": "ck_run_physical_18b3405cc1",'
        ' "relation": "ops.run"}, {"expression": "(input_revision >= 0)", "na'
        'me": "ck_run_physical_cf2108479f", "relation": "ops.run"}, {"express'
        'ion": "(\\"position\\" >= 0)", "name": "ck_run_source_view_physical_90'
        '39b28f88", "relation": "ops.run_source_view"}, {"expression": "(atte'
        'mpt >= 0)", "name": "ck_task_physical_3f232544ec", "relation": "ops.'
        'task"}, {"expression": "(invocation_key <> \'\'\'\'::text)", "name": "ck'
        '_task_physical_8afd8b30fe", "relation": "ops.task"}, {"expression": '
        "\"(status = ANY (ARRAY[''pending''::text, ''running''::text, ''awaiti"
        "ng_agent''::text, ''done''::text, ''empty''::text, ''failed''::text,"
        " ''reused''::text, ''skipped''::text, ''cancelled''::text]))\", \"name"
        '": "ck_task_physical_8cb2ac785d", "relation": "ops.task"}, {"express'
        'ion": "(task_id <> dependency_task_id)", "name": "ck_task_dependency'
        '_physical_64bb43e797", "relation": "ops.task_dependency"}, {"express'
        "ion\": \"(kind = ANY (ARRAY[''ancestor_source_view''::text, ''source_v"
        "iew_interpretation''::text, ''source_view_product''::text]))\", \"name"
        '": "ck_task_dependency_physical_c683b2f601", "relation": "ops.task_d'
        "ependency\"}, {\"expression\": \"(branch = ANY (ARRAY[''if''::text, ''th"
        "en''::text, ''else''::text]))\", \"name\": \"ck_conditional_atom_physica"
        'l_7349b348ce", "relation": "sem.conditional_atom"}, {"expression": "'
        '(\\"position\\" >= 0)", "name": "ck_conditional_atom_physical_80eec7c0'
        'dc", "relation": "sem.conditional_atom"}, {"expression": "((choices '
        "IS NULL) OR (choices = ''null''::jsonb) OR (jsonb_typeof(choices) = "
        "''array''::text))\", \"name\": \"ck_conditional_atom_physical_84f8e0b15f"
        '", "relation": "sem.conditional_atom"}, {"expression": "(presence = '
        "ANY (ARRAY[''present''::text, ''absent''::text, ''optional''::text])"
        ')", "name": "ck_conditional_atom_physical_9beafb7d1a", "relation": "'
        'sem.conditional_atom"}, {"expression": "(scope = ANY (ARRAY[\'\'shape\''
        "'::text, ''accepted_value''::text]))\", \"name\": \"ck_conditional_rule_"
        'physical_e64beec5ee", "relation": "sem.conditional_rule"}, {"express'
        'ion": "(\\"position\\" >= 0)", "name": "ck_identity_slot_physical_9039'
        'b28f88", "relation": "sem.identity_slot"}, {"expression": "((minimum'
        "_cardinality IS NULL) OR (maximum_cardinality IS NULL) OR (minimum_c"
        'ardinality <= maximum_cardinality))", "name": "ck_property_applicabi'
        'lity_physical_62e5012383", "relation": "sem.property_applicability"}'
        ', {"expression": "((maximum_cardinality IS NULL) OR (maximum_cardina'
        'lity >= 0))", "name": "ck_property_applicability_physical_8e24e7a9f5'
        '", "relation": "sem.property_applicability"}, {"expression": "((mini'
        'mum_cardinality IS NULL) OR (minimum_cardinality >= 0))", "name": "c'
        'k_property_applicability_physical_dd48c61c63", "relation": "sem.prop'
        "erty_applicability\"}, {\"expression\": \"(input_kind = ''dependency''::"
        'text)", "name": "ck_sql_admission_physical_022451ced1", "relation": '
        "\"sem.sql_admission\"}]'::jsonb,'e1337dfa3f18c89ab7b5cbf1de1a8bcb786d9"
        "96a7759b2f224af27d3004ad9a0')"
    )
    op.execute(
        "GRANT SELECT ON sem.runtime_binding TO corpus_sem_writer,corpus_sem_"
        "reader,corpus_sem_admitter,corpus_sem_evaluator"
    )
    op.execute("SET LOCAL ROLE " + op.get_bind().dialect.identifier_preparer.quote(_migration_role))
    for transition in state["operations"]:
        Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(transition))
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))


def downgrade():
    raise RuntimeError("destructive runtime binding downgrade refused")
