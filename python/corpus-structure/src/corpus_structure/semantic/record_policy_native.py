"""Native policy issuer recognition and bounded ordinary provenance disclosure."""

GRADE_SCHEMA_SOURCE = "native/data-operation-record-grade.schema.json"
EVENT_FRAME_SCHEMA_SOURCE = "native/data-operation-operation-event-frame.schema.json"
EVENT_FRAME_KIND = (
    "https://corpus-structure.dev/semantic/operation-events/protected/DdoOperationEventFrame"
)
EVENT_FRAME_OPERATION = "operation_event.frame"
EVENT_FRAME_FACTORY = "corpus_structure.methods.operation_events.OperationEventFrame.acquire_port"


def _fit_frame_schema(model, prefix):
    from pydantic import TypeAdapter

    from .data_operation_parameters import _draft7
    from .data_operation_wire import checked_json_schema
    from .identity import canonical_bytes
    from .nominal_schema_kinds import _tuples

    schema = TypeAdapter(model).json_schema(ref_template="#/definitions/" + prefix + "_{model}")
    definitions = schema.pop("$defs", {})
    schema["definitions"] = {prefix + "_" + name: value for name, value in definitions.items()}
    return canonical_bytes(checked_json_schema(_draft7(_tuples(schema))))


def record_policy_grade_schema() -> bytes:
    """Capture the actual protected grade DTO with collision-free Draft7 refs."""
    from corpus_structure.evaluate.declared_record_policy import DdoRecordGrade

    return _fit_frame_schema(DdoRecordGrade, "record_grade")


def operation_event_frame_schema() -> bytes:
    """Capture the current frame owner; native acquisition authenticates the selection."""
    from corpus_structure.evaluate.selected_operation_events import DdoOperationEventFrame

    return _fit_frame_schema(DdoOperationEventFrame, "operation_event_frame")


def read_selected_feature_fit_frame(
    connection,
    *,
    variant,
    project_id,
    demand_id,
    read_id,
    use_id,
    derivation_id,
    product_id,
    expected_cut,
    frame_digest,
    cut,
    max_bytes=8388608,
):
    """Read one native-authenticated fit partition using an actual fitter login."""
    import json
    from typing import cast

    from ._data_operation_wire import WireReadSelectedFeatureFitFrameRequest
    from .data_operation_json import json_bytes
    from .data_operation_storage import DataOperationStorage
    from .data_operation_wire import validate_native_wire
    from .demand_results import CutSelection
    from .identity import canonical_bytes

    if not isinstance(cut, CutSelection) or cut.identity != expected_cut:
        raise ValueError("feature fit requires the exact retained cut bytes")
    pins = cut.record
    if (pins["project_id"], pins["demand_id"], pins["read_id"]) != (project_id, demand_id, read_id):
        raise ValueError("feature fit cut belongs to another selection")
    payload = dict(
        variant=variant,
        project_id=project_id,
        demand_id=demand_id,
        read_id=read_id,
        use_id=use_id,
        derivation_id=derivation_id,
        product_id=product_id,
        expected_cut=expected_cut,
        frame_digest=frame_digest,
        cut_canonical_json=cut.content.decode(),
        max_bytes=max_bytes,
    )
    request = cast(
        WireReadSelectedFeatureFitFrameRequest,
        validate_native_wire("read_selected_feature_fit_frame", "input", payload),
    )
    result = DataOperationStorage(connection).read_selected_feature_fit_frame(request)
    if CutSelection(json_bytes(result["cut"])).record != pins:
        raise ValueError("feature fit returned another retained cut")
    if (
        result["variant"] != variant
        or result["product_id"] != product_id
        or result["derivation_id"] != derivation_id
        or result["frame"]["frame_digest"] != frame_digest
    ):
        raise ValueError("feature fit returned another protected frame")
    # JSONB is a projection of the semantic body and can normalize signed zero.
    # The authenticated CPU grade retains its original exact frame text. Native
    # compares that text's parsed value and digest before disclosing it; restoring
    # its typed frame here preserves the actual numerical basis without guessing
    # PostgreSQL's float spelling or granting authority to caller-supplied bytes.
    if variant == "record-feature-grade":
        from corpus_structure.evaluate.declared_record_policy import DdoRecordGrade

        frame_model = DdoRecordGrade
    elif variant == "operation-event-frame":
        from corpus_structure.evaluate.selected_operation_events import DdoOperationEventFrame

        frame_model = DdoOperationEventFrame
    else:
        raise ValueError("unknown selected feature fit frame variant")
    grade = result["frame"]
    restored = frame_model.model_validate_json(
        canonical_bytes(
            {
                **grade,
                "frame": json.loads(grade["frame_canonical_json"]),
            }
        ),
        strict=True,
    )
    return {**result, "frame": restored.model_dump(mode="json")}


def record_policy_native_sql():
    import json
    from dataclasses import asdict

    from .declared_structural_admission import ADMISSION_KIND
    from .record_policy_authority import (
        AUTHORIZATION_EFFECT,
        AUTHORIZATION_FACTORY,
        AUTHORIZATION_KIND,
        AUTHORIZATION_OPERATION,
    )

    return (
        r"""
CREATE OR REPLACE FUNCTION ops.ddo_policy_command_eligible(definition sem.data_operation_definition)
RETURNS boolean LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $policy$
 SELECT definition.operation_id='__OPERATION__' AND definition.profile='command'
 AND definition.support_contract->'capabilities'->>'preparation'='native-publication'
 AND definition.support_contract->'capabilities'->'forms'='["scalar"]'::jsonb
 AND definition.support_contract->'capabilities'->'prepared_factory'->>'entrypoint'='__FACTORY__'
 AND definition.support_contract->'effects'='__EFFECTS__'::jsonb
 AND definition.support_contract->'capabilities'->'prepared_factory'->>'source_digest' ~ '^[0-9a-f]{64}$'
 AND definition.implementation_revision LIKE 'implementation-slice:%'
$policy$;
REVOKE ALL ON FUNCTION ops.ddo_policy_command_eligible(sem.data_operation_definition) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.ddo_policy_authority_leaf(episode text) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $policy$
 SELECT NOT pg_has_role(coalesce(nullif(current_setting('role'),'none'),session_user),'corpus_sem_evaluator','MEMBER')
 AND EXISTS(SELECT FROM ops.data_derivation d JOIN ops.data_request request ON request.id=d.request_id
 JOIN sem.data_operation_definition definition ON definition.release_id=d.release_id AND definition.operation_id=request.operation_id
 JOIN ops.data_publication_receipt receipt ON receipt.derivation_id=d.id AND receipt.intent_id=d.intent_id
 JOIN ops.data_derivation_output output ON output.derivation_id=d.id
 JOIN sem.data_kind_contract kind ON kind.kind_contract=(SELECT product.kind_contract FROM kb.data_product product WHERE product.id=output.product_id)
 WHERE d.id=episode AND d.outcome='success'
 AND ((ops.ddo_policy_command_eligible(definition) AND output.role='authorization' AND kind.kind='__KIND__')
 OR (ops.ddo_structural_command_eligible(definition) AND output.role='admission' AND kind.kind='__STRUCTURAL_KIND__'))
 AND output.position=0 AND output.multiplicity=1 AND output.member_id IS NULL
 AND kind.universe='ordinary'
 AND (SELECT count(*) FROM ops.data_derivation_output other WHERE other.derivation_id=d.id)=1)
$policy$;
REVOKE ALL ON FUNCTION ops.ddo_policy_authority_leaf(text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.ddo_policy_authority_summary(episode text,selected_use text,read_id text) RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $policy$
DECLARE d ops.data_derivation; chosen ops.demand_use; boundary ops.data_demand_read;
 output ops.data_derivation_output; receipt ops.data_publication_receipt; standing text;
BEGIN
 IF NOT coalesce(ops.ddo_policy_authority_leaf(episode),false) THEN
 RAISE EXCEPTION 'ordinary policy authority summary requires an authenticated native issuer' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT boundary FROM ops.data_demand_read WHERE id=read_id;
 SELECT * INTO STRICT d FROM ops.data_derivation WHERE id=episode;
 -- Publication records its fulfilled demand uses in the same transaction as
 -- the episode. Those immutable rows carry the full transaction visibility
 -- marker; the episode itself carries only its completion timestamp.
 IF d.completed_at>boundary.frontier_at OR NOT EXISTS(
 SELECT FROM ops.demand_use published WHERE published.derivation_id=d.id
 AND published.fate='fulfilled'
 AND ops.ddo_read_visible(published.created_at,published.created_xid,boundary)) THEN
 RAISE EXCEPTION 'policy issuer is outside selected native visibility' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT output FROM ops.data_derivation_output WHERE derivation_id=episode;
 SELECT * INTO STRICT receipt FROM ops.data_publication_receipt WHERE derivation_id=episode AND intent_id=d.intent_id;
 IF selected_use IS NOT NULL THEN
 SELECT * INTO STRICT chosen FROM ops.demand_use WHERE id=selected_use AND derivation_id=episode;
 IF NOT ops.ddo_read_visible(chosen.created_at,chosen.created_xid,boundary) THEN
 RAISE EXCEPTION 'policy authority use is outside selected native visibility' USING ERRCODE='23514'; END IF;
 standing:=CASE WHEN ops.ddo_use_valid(chosen,boundary) THEN 'valid' ELSE 'unavailable' END;
 ELSE standing:=CASE WHEN ops.ddo_support_valid(episode,boundary) THEN 'valid' ELSE 'unavailable' END;
 END IF;
 RETURN jsonb_build_object('format','ddo-native-authority-leaf-v1','derivation_id',episode,
 'use_id',selected_use,'issuer_operation',(SELECT operation_id FROM ops.data_request WHERE id=d.request_id),'release_id',d.release_id,'runtime_id',d.runtime_id,
 'recipe',d.recipe,'product_id',output.product_id,
 'kind_contract',(SELECT kind_contract FROM kb.data_product WHERE id=output.product_id),
 'intent_id',d.intent_id,'receipt_id',receipt.id,'standing',standing,'protected_dependencies','undisclosed');
END $policy$;
REVOKE ALL ON FUNCTION ops.ddo_policy_authority_summary(text,text,text) FROM PUBLIC;
""".replace("__OPERATION__", AUTHORIZATION_OPERATION)
        .replace("__FACTORY__", AUTHORIZATION_FACTORY)
        .replace("__KIND__", AUTHORIZATION_KIND)
        .replace("__STRUCTURAL_KIND__", ADMISSION_KIND)
        .replace("__EFFECTS__", json.dumps([asdict(AUTHORIZATION_EFFECT)], separators=(",", ":")))
        + _feature_fit_sql()
    )


def _feature_fit_sql():
    from .record_policy_authority import GRADE_FACTORY, GRADE_KIND, GRADE_OPERATION

    return (
        r"""
CREATE OR REPLACE FUNCTION ops.ddo_require_feature_fit_principal() RETURNS void
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fit$
DECLARE principal name:=session_user;
BEGIN
 IF NOT pg_has_role(principal,'corpus_sem_fitter','USAGE')
 OR current_setting('role') NOT IN ('none',principal::text)
 OR pg_has_role(principal,'corpus_sem_evaluator','MEMBER')
 OR pg_has_role(principal,'corpus_sem_publisher','MEMBER')
 OR has_database_privilege(principal,current_database(),'TEMP')
 OR EXISTS(SELECT FROM pg_roles WHERE oid=principal::regrole
 AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolbypassrls OR rolreplication))
 OR EXISTS(SELECT FROM pg_namespace WHERE nspname IN ('sem','data','ops','kb','eval')
 AND (pg_has_role(principal,nspowner,'MEMBER') OR has_schema_privilege(principal,oid,'CREATE')))
 OR EXISTS(SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname IN ('ops','kb','eval') AND c.relkind IN ('r','p','v','m')
 AND (has_table_privilege(principal,c.oid,'SELECT') OR has_any_column_privilege(principal,c.oid,'SELECT'))) THEN
 RAISE EXCEPTION 'feature fitting requires a restricted actual fitting principal' USING ERRCODE='42501'; END IF;
END $fit$;
REVOKE ALL ON FUNCTION ops.ddo_require_feature_fit_principal() FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.ddo_feature_fit_body_access(contract text,body jsonb) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fit$
BEGIN
 PERFORM ops.ddo_require_feature_fit_principal();
 RETURN EXISTS(SELECT FROM sem.data_kind_contract kind WHERE kind.kind_contract=contract
 AND kind.universe='evaluator' AND (
 (kind.kind='__GRADE_KIND__' AND data.ddo_json(body)->>'version'='record-grade-1'
 AND data.ddo_json(body)->'frame'->>'partition'='feature_fit') OR
 (kind.kind='__EVENT_FRAME_KIND__' AND data.ddo_json(body)->>'version'='selected-operation-event-frame-product-1'
 AND data.ddo_json(body)->'frame'->'question'->>'partition' IN ('development','feature_fit'))));
END $fit$;
REVOKE ALL ON FUNCTION ops.ddo_feature_fit_body_access(text,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.read_selected_feature_fit_frame(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fit$
DECLARE p jsonb:=p_payload; d ops.data_demand; boundary ops.data_demand_read;
 p_use text:=p->>'use_id'; p_product text:=p->>'product_id'; p_derivation text:=p->>'derivation_id';
 scope_key text; epoch bigint; snapshot jsonb:='{}'; admitted boolean; cut jsonb;
 grade jsonb; receipt_id text; result jsonb; definition sem.data_operation_definition;
 episode ops.data_derivation; intent ops.data_completion_intent; variant text:=p->>'variant';
 expected_operation text; expected_factory text; expected_kind text; expected_role text;
BEGIN
 PERFORM ops.ddo_require_feature_fit_principal();
 CASE variant
 WHEN 'record-feature-grade' THEN
 expected_operation:='__GRADE_OPERATION__'; expected_factory:='__GRADE_FACTORY__';
 expected_kind:='__GRADE_KIND__'; expected_role:='grade';
 WHEN 'operation-event-frame' THEN
 expected_operation:='__EVENT_FRAME_OPERATION__'; expected_factory:='__EVENT_FRAME_FACTORY__';
 expected_kind:='__EVENT_FRAME_KIND__'; expected_role:='frame';
 ELSE RAISE EXCEPTION 'unknown selected feature fit frame variant' USING ERRCODE='23514';
 END CASE;
 SELECT * INTO STRICT d FROM ops.data_demand WHERE id=p->>'demand_id' AND project_id=p->>'project_id';
 SELECT * INTO STRICT boundary FROM ops.data_demand_read WHERE id=p->>'read_id' AND demand_id=d.id;
 p:=p||jsonb_build_object('scope',boundary.scope);
 FOR scope_key IN __DDO_CORE_SUPPORT_SCOPES__ LOOP
 SELECT s.epoch INTO STRICT epoch FROM ops.data_trust_scope s WHERE s.scope=scope_key AND s.project_id=d.project_id FOR SHARE;
 snapshot:=snapshot||jsonb_build_object(scope_key,epoch);
 END LOOP;
 IF ops.ddo_trust_snapshot_meaning(snapshot) IS DISTINCT FROM ops.ddo_trust_snapshot_meaning(boundary.trust_snapshot) THEN
 RAISE EXCEPTION 'feature fit current trust differs from retained cut' USING ERRCODE='23514'; END IF;
 __DDO_CORE_SELECTED_FEATURE_FIT_OUTPUT__ INTO admitted;
 IF NOT coalesce(admitted,false) THEN
 RAISE EXCEPTION 'feature fit grade is outside exact current selected support' USING ERRCODE='23514'; END IF;
 __DDO_CORE_CUT_SELECTION__ INTO cut;
 IF (p->>'cut_canonical_json')::jsonb IS DISTINCT FROM cut
 OR p->>'expected_cut' IS DISTINCT FROM 'cut-selection:'||encode(sha256(convert_to(p->>'cut_canonical_json','UTF8')),'hex') THEN
 RAISE EXCEPTION 'feature fit cut bytes or native pins differ' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT episode FROM ops.data_derivation WHERE id=p_derivation AND outcome='success';
 SELECT operation.* INTO STRICT definition FROM sem.data_operation_definition operation
 JOIN ops.data_request request ON request.release_id=operation.release_id AND request.operation_id=operation.operation_id
 WHERE request.id=episode.request_id AND request.project_id=d.project_id;
 SELECT * INTO STRICT intent FROM ops.data_completion_intent WHERE id=episode.intent_id;
 SELECT receipt.id INTO STRICT receipt_id FROM ops.data_publication_receipt receipt
 JOIN ops.data_derivation_output output ON output.derivation_id=receipt.derivation_id
 WHERE receipt.derivation_id=episode.id AND receipt.intent_id=episode.intent_id
 AND output.product_id=p_product AND output.member_id IS NULL AND output.role=expected_role
 AND output.position=0 AND output.multiplicity=1;
 IF definition.operation_id IS DISTINCT FROM expected_operation
 OR definition.profile IS DISTINCT FROM 'derivation'
 OR definition.support_contract->'effects' IS DISTINCT FROM '[]'::jsonb
 OR definition.support_contract->'capabilities'->'prepared_factory'->>'entrypoint' IS DISTINCT FROM expected_factory
 OR (definition.support_contract->'capabilities'->'prepared_factory'->>'source_digest' ~ '^[0-9a-f]{64}$') IS NOT TRUE
 OR (definition.implementation_revision LIKE 'implementation-slice:%') IS NOT TRUE
 OR intent.payload->>'implementation_revision' IS DISTINCT FROM definition.implementation_revision
 OR jsonb_array_length(coalesce(intent.payload->'execution_evidence'->'cpu_receipts','[]'))<>1
 OR episode.recipe IS DISTINCT FROM definition.recipe THEN
 RAISE EXCEPTION 'feature fit requires the actual admitted protected grade implementation' USING ERRCODE='23514'; END IF;
 IF NOT EXISTS(SELECT FROM kb.data_product product JOIN sem.data_kind_contract kind
 ON kind.kind_contract=product.kind_contract WHERE product.id=p_product AND product.project_id=d.project_id
 AND kind.kind=expected_kind AND kind.universe='evaluator') THEN
 RAISE EXCEPTION 'feature fit variant differs from actual protected frame kind' USING ERRCODE='23514'; END IF;
 SELECT data.ddo_json(product.canonical_body) INTO STRICT grade FROM kb.data_product product WHERE id=p_product AND project_id=d.project_id;
 IF grade->>'frame_digest' IS DISTINCT FROM p->>'frame_digest'
 OR grade->>'frame_digest' IS DISTINCT FROM encode(sha256(convert_to(grade->>'frame_canonical_json','UTF8')),'hex')
 OR (grade->>'frame_canonical_json')::jsonb IS DISTINCT FROM grade->'frame'
 OR (CASE variant WHEN 'record-feature-grade' THEN grade->'frame'->>'project_id'
 ELSE grade->'frame'->'question'->'prediction_selection'->>'project_id' END) IS DISTINCT FROM d.project_id THEN
 RAISE EXCEPTION 'feature fit grade canonical frame differs' USING ERRCODE='23514'; END IF;
 result:=jsonb_build_object('variant',variant,'cut',cut,'product_id',p_product,'derivation_id',p_derivation,'receipt_id',receipt_id,'frame',grade);
 IF octet_length(data.canonical_json(result))>coalesce((p->>'max_bytes')::bigint,8388608) THEN
 RAISE EXCEPTION 'feature fit frame exceeds explicit byte bound' USING ERRCODE='23514'; END IF;
 RETURN result;
END $fit$;
REVOKE ALL ON FUNCTION ops.read_selected_feature_fit_frame(jsonb) FROM PUBLIC;
""".replace("__GRADE_KIND__", GRADE_KIND)
        .replace("__GRADE_OPERATION__", GRADE_OPERATION)
        .replace("__GRADE_FACTORY__", GRADE_FACTORY)
        .replace("__EVENT_FRAME_KIND__", EVENT_FRAME_KIND)
        .replace("__EVENT_FRAME_OPERATION__", EVENT_FRAME_OPERATION)
        .replace("__EVENT_FRAME_FACTORY__", EVENT_FRAME_FACTORY)
    )
