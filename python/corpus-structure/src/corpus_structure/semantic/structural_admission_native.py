"""Exact tagged structural statement lowering and protected native admission guards."""


def structural_statement_native_sql():
    """Preserve typed scalar subtrees; no JSONB numeric roundtrip supplies meaning."""
    return r"""
CREATE OR REPLACE FUNCTION ops.ddo_structural_map(fields jsonb) RETURNS jsonb
LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $structural$
 SELECT data.ddo_normalize(jsonb_build_array('mapping',coalesce(jsonb_agg(pair),'[]')))
 FROM jsonb_array_elements(fields) pair WHERE pair->1 IS NOT NULL
$structural$;

CREATE OR REPLACE FUNCTION ops.ddo_structural_pick(value jsonb,names text[],exclude_names boolean DEFAULT false) RETURNS jsonb
LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $structural$
 SELECT ops.ddo_structural_map(coalesce(jsonb_agg(pair),'[]')) FROM jsonb_array_elements(value->1) pair
 WHERE ((pair->>0=ANY(names))<>exclude_names) AND pair->1<>'["null"]'::jsonb
$structural$;

CREATE OR REPLACE FUNCTION ops.ddo_structural_merge(left_value jsonb,right_value jsonb) RETURNS jsonb
LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $structural$
 SELECT ops.ddo_structural_map(coalesce(jsonb_agg(pair),'[]')) FROM (
 SELECT DISTINCT ON (pair->>0) pair FROM (
 SELECT pair,0 priority FROM jsonb_array_elements(left_value->1) pair
 UNION ALL SELECT pair,1 FROM jsonb_array_elements(right_value->1) pair) fields
 ORDER BY pair->>0,priority DESC) chosen
$structural$;

CREATE OR REPLACE FUNCTION ops.ddo_structural_citation(report jsonb,identifier text) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $structural$
DECLARE passage jsonb; source_value jsonb;
BEGIN
 SELECT value INTO STRICT passage FROM jsonb_array_elements(data.ddo_field(data.ddo_field(report,'inputs'),'passages')->1)
 WHERE data.ddo_field(value,'passage_id')->>1=identifier;
 SELECT value INTO STRICT source_value FROM jsonb_array_elements(data.ddo_field(data.ddo_field(report,'inputs'),'sources')->1)
 WHERE ops.ddo_digest(data.ddo_json(ops.ddo_structural_pick(value,ARRAY[]::text[],true)))=data.ddo_field(passage,'source_ref')->>1;
 RETURN ops.ddo_structural_merge(ops.ddo_structural_pick(passage,ARRAY['passage_id','source_ref'],true),
 ops.ddo_structural_map(jsonb_build_array(jsonb_build_array('source',ops.ddo_structural_pick(source_value,ARRAY[]::text[],true)))));
END $structural$;

CREATE OR REPLACE FUNCTION ops.ddo_structural_span(report jsonb,span_value jsonb) RETURNS jsonb
LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $structural$
 SELECT ops.ddo_structural_merge(ops.ddo_structural_citation(report,data.ddo_field(span_value,'passage_id')->>1),
 ops.ddo_structural_pick(span_value,ARRAY['passage_id'],true))
$structural$;

CREATE OR REPLACE FUNCTION ops.ddo_structural_citations(report jsonb,identifiers jsonb) RETURNS jsonb
LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $structural$
 SELECT jsonb_build_array('sequence',coalesce(jsonb_agg(citation ORDER BY data.canonical_json(data.ddo_json(citation)) COLLATE "C"),'[]'))
 FROM (SELECT DISTINCT ops.ddo_structural_citation(report,value->>1) citation FROM jsonb_array_elements(identifiers->1)) citations
$structural$;

CREATE OR REPLACE FUNCTION ops.ddo_structural_clause_field(report jsonb,field_value jsonb) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $structural$
DECLARE fields jsonb; typed_value jsonb; spans jsonb;
BEGIN
 fields:=jsonb_build_array(
 jsonb_build_array('dimension',data.ddo_field(field_value,'dimension')),
 jsonb_build_array('lexical_value',data.ddo_field(field_value,'lexical_value')),
 jsonb_build_array('evidence',ops.ddo_structural_citations(report,data.ddo_field(field_value,'evidence'))));
 IF coalesce(data.ddo_field(field_value,'span'),'["null"]')<>'["null"]'::jsonb THEN
 fields:=fields||jsonb_build_array(jsonb_build_array('span',ops.ddo_structural_span(report,data.ddo_field(field_value,'span')))); END IF;
 IF coalesce(data.ddo_field(field_value,'spans'),'["null"]')<>'["null"]'::jsonb THEN
 SELECT jsonb_build_array('sequence',coalesce(jsonb_agg(ops.ddo_structural_span(report,value) ORDER BY ordinal),'[]')) INTO spans
 FROM jsonb_array_elements(data.ddo_field(field_value,'spans')->1) WITH ORDINALITY selected(value,ordinal);
 fields:=fields||jsonb_build_array(jsonb_build_array('spans',spans)); END IF;
 IF coalesce(data.ddo_field(field_value,'literal'),'["null"]')<>'["null"]'::jsonb THEN
 fields:=fields||jsonb_build_array(jsonb_build_array('literal',ops.ddo_structural_pick(data.ddo_field(field_value,'literal'),ARRAY[]::text[],true))); END IF;
 -- This is a free JSON condition subtree: preserve its exact tags and nulls.
 IF coalesce(data.ddo_field(field_value,'condition'),'["null"]')<>'["null"]'::jsonb THEN
 fields:=fields||jsonb_build_array(jsonb_build_array('condition',data.ddo_field(field_value,'condition'))); END IF;
 typed_value:=data.ddo_field(field_value,'typed');
 IF coalesce(typed_value,'["null"]')<>'["null"]'::jsonb THEN
 typed_value:=ops.ddo_structural_merge(ops.ddo_structural_pick(typed_value,ARRAY['span','basis_evidence'],true),
 ops.ddo_structural_map(jsonb_build_array(jsonb_build_array('span',ops.ddo_structural_span(report,data.ddo_field(typed_value,'span'))))));
 IF coalesce(data.ddo_field(data.ddo_field(field_value,'typed'),'basis_evidence'),'["null"]')<>'["null"]'::jsonb THEN
 typed_value:=ops.ddo_structural_merge(typed_value,ops.ddo_structural_map(jsonb_build_array(jsonb_build_array('basis_evidence',
 ops.ddo_structural_span(report,data.ddo_field(data.ddo_field(field_value,'typed'),'basis_evidence')))))); END IF;
 fields:=fields||jsonb_build_array(jsonb_build_array('typed',typed_value)); END IF;
 RETURN ops.ddo_structural_map(fields);
END $structural$;

CREATE OR REPLACE FUNCTION ops.ddo_structural_comparison_statement(report jsonb) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $structural$
DECLARE inputs jsonb:=data.ddo_field(report,'inputs'); comparison jsonb:=data.ddo_field(report,'comparison');
 fields jsonb; dimensions jsonb:='[]'; dimension jsonb; entry jsonb; side text; value jsonb; group_value jsonb; members jsonb; witnesses jsonb;
 coverage jsonb; exclusions jsonb; succession jsonb;
BEGIN
 IF data.ddo_field(report,'kind')->>1 IS DISTINCT FROM 'qualified_comparison' THEN
 RAISE EXCEPTION 'structural admission requires the exact qualified comparison variant' USING ERRCODE='23514'; END IF;
 SELECT jsonb_build_array('sequence',coalesce(jsonb_agg(coverage_item.item ORDER BY (coverage_item.item->>1) COLLATE "C"),'[]')) INTO coverage
 FROM jsonb_array_elements(data.ddo_field(inputs,'coverage_limits')->1) coverage_item(item);
 SELECT jsonb_build_array('sequence',coalesce(jsonb_agg(selected.item ORDER BY data.canonical_json(data.ddo_json(selected.item)) COLLATE "C"),'[]')) INTO exclusions FROM (
 SELECT ops.ddo_structural_map(jsonb_build_array(
 jsonb_build_array('left',ops.ddo_structural_citation(report,data.ddo_field(exclusion,'left')->>1)),
 jsonb_build_array('right',ops.ddo_structural_citation(report,data.ddo_field(exclusion,'right')->>1)))) value
 FROM jsonb_array_elements(data.ddo_field(inputs,'exclusions')->1) exclusion) selected(item);
 FOR dimension IN SELECT item FROM jsonb_array_elements(data.ddo_field(comparison,'dimensions')->1) item LOOP
 entry:=ops.ddo_structural_pick(dimension,ARRAY['dimension','outcome','typed_outcome','assumptions','grouping_outcome','member_comparisons']);
 FOREACH side IN ARRAY ARRAY['removed_interval','added_interval'] LOOP
 value:=data.ddo_field(dimension,side);
 IF coalesce(value,'["null"]')<>'["null"]'::jsonb THEN
 entry:=ops.ddo_structural_merge(entry,ops.ddo_structural_map(jsonb_build_array(jsonb_build_array(side,ops.ddo_structural_pick(value,ARRAY[]::text[],true))))); END IF;
 END LOOP;
 FOREACH side IN ARRAY ARRAY['left','right'] LOOP
 value:=data.ddo_field(dimension,side);
 IF coalesce(value,'["null"]')<>'["null"]'::jsonb THEN
 entry:=ops.ddo_structural_merge(entry,ops.ddo_structural_map(jsonb_build_array(jsonb_build_array(side,ops.ddo_structural_clause_field(report,value))))); END IF;
 group_value:=data.ddo_field(dimension,side||'_group');
 IF coalesce(group_value,'["null"]')<>'["null"]'::jsonb THEN
 SELECT jsonb_build_array('sequence',coalesce(jsonb_agg(ops.ddo_structural_clause_field(report,item) ORDER BY ordinal),'[]')) INTO members
 FROM jsonb_array_elements(data.ddo_field(group_value,'members')->1) WITH ORDINALITY selected(item,ordinal);
 SELECT jsonb_build_array('sequence',coalesce(jsonb_agg(ops.ddo_structural_span(report,item) ORDER BY ordinal),'[]')) INTO witnesses
 FROM jsonb_array_elements(data.ddo_field(group_value,'witnesses')->1) WITH ORDINALITY selected(item,ordinal);
 value:=ops.ddo_structural_merge(ops.ddo_structural_pick(group_value,ARRAY['state','grouping']),ops.ddo_structural_map(jsonb_build_array(
 jsonb_build_array('members',members),jsonb_build_array('witnesses',witnesses))));
 entry:=ops.ddo_structural_merge(entry,ops.ddo_structural_map(jsonb_build_array(jsonb_build_array(side||'_group',value)))); END IF;
 END LOOP;
 dimensions:=dimensions||jsonb_build_array(entry);
 END LOOP;
 fields:=jsonb_build_array(
 jsonb_build_array('left',ops.ddo_structural_citation(report,data.ddo_field(comparison,'left_id')->>1)),
 jsonb_build_array('right',ops.ddo_structural_citation(report,data.ddo_field(comparison,'right_id')->>1)),
 jsonb_build_array('dimensions',jsonb_build_array('sequence',dimensions)));
 value:=ops.ddo_structural_merge(ops.ddo_structural_pick(comparison,ARRAY['equivalence','identity_standing','applicability']),ops.ddo_structural_map(fields));
 succession:=data.ddo_field(comparison,'succession');
 IF coalesce(succession,'["null"]')<>'["null"]'::jsonb THEN
 value:=ops.ddo_structural_merge(value,ops.ddo_structural_map(jsonb_build_array(jsonb_build_array('succession',ops.ddo_structural_map(jsonb_build_array(
 jsonb_build_array('older',ops.ddo_structural_citation(report,data.ddo_field(succession,'older_id')->>1)),
 jsonb_build_array('newer',ops.ddo_structural_citation(report,data.ddo_field(succession,'newer_id')->>1)),
 jsonb_build_array('evidence',ops.ddo_structural_span(report,data.ddo_field(succession,'evidence'))),
 jsonb_build_array('older_evidence',ops.ddo_structural_span(report,data.ddo_field(succession,'older_evidence'))))))))); END IF;
 RETURN ops.ddo_structural_merge(ops.ddo_structural_pick(inputs,ARRAY['scope','inventory_id']),ops.ddo_structural_map(jsonb_build_array(
 jsonb_build_array('version',jsonb_build_array('string','structural-public-statement-3')),
 jsonb_build_array('kind',jsonb_build_array('string','qualified_comparison')),
 jsonb_build_array('input_policy_id',data.ddo_field(inputs,'policy_id')),
 jsonb_build_array('coverage_limits',coverage),jsonb_build_array('exclusions',exclusions),jsonb_build_array('comparison',value))));
END $structural$;

CREATE OR REPLACE FUNCTION ops.ddo_structural_statement(report jsonb,component_id text) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $structural$
DECLARE inputs jsonb:=data.ddo_field(report,'inputs'); variant text:=data.ddo_field(report,'kind')->>1;
 coverage jsonb; exclusions jsonb; statement jsonb; value jsonb; component jsonb; fields jsonb; role_name text; citations jsonb;
BEGIN
 IF variant='qualified_comparison' THEN
 IF component_id IS NOT NULL THEN RAISE EXCEPTION 'comparison statement cannot select a definition component' USING ERRCODE='23514'; END IF;
 RETURN ops.ddo_structural_comparison_statement(report); END IF;
 IF variant NOT IN ('condition_qualification','definition_components') THEN
 RAISE EXCEPTION 'structural admission requires its exact released report variant' USING ERRCODE='23514'; END IF;
 IF (variant='definition_components') IS DISTINCT FROM (component_id IS NOT NULL) THEN
 RAISE EXCEPTION 'only definition publication requires one exact component selector' USING ERRCODE='23514'; END IF;
 SELECT jsonb_build_array('sequence',coalesce(jsonb_agg(item ORDER BY (item->>1) COLLATE "C"),'[]')) INTO coverage
 FROM jsonb_array_elements(data.ddo_field(inputs,'coverage_limits')->1) selected(item);
 SELECT jsonb_build_array('sequence',coalesce(jsonb_agg(item ORDER BY data.canonical_json(data.ddo_json(item)) COLLATE "C"),'[]')) INTO exclusions FROM (
 SELECT ops.ddo_structural_map(jsonb_build_array(
 jsonb_build_array('left',ops.ddo_structural_citation(report,data.ddo_field(exclusion,'left')->>1)),
 jsonb_build_array('right',ops.ddo_structural_citation(report,data.ddo_field(exclusion,'right')->>1)))) item
 FROM jsonb_array_elements(data.ddo_field(inputs,'exclusions')->1) selected(exclusion)) selected;
 statement:=ops.ddo_structural_map(jsonb_build_array(
 jsonb_build_array('version',jsonb_build_array('string','structural-public-statement-3')),
 jsonb_build_array('kind',jsonb_build_array('string',variant)),jsonb_build_array('scope',data.ddo_field(inputs,'scope')),
 jsonb_build_array('coverage_limits',coverage),jsonb_build_array('exclusions',exclusions)));
 IF variant='definition_components' THEN
 SELECT item INTO STRICT component FROM jsonb_array_elements(data.ddo_field(data.ddo_field(report,'definition_components'),'components')->1) selected(item)
 WHERE data.ddo_field(item,'component_id')->>1=component_id;
 fields:=jsonb_build_array(jsonb_build_array('term',ops.ddo_structural_span(report,data.ddo_field(component,'term'))),
 jsonb_build_array('content',ops.ddo_structural_span(report,data.ddo_field(component,'content'))),
 jsonb_build_array('interpretation',data.ddo_field(component,'interpretation')),jsonb_build_array('scope',data.ddo_field(component,'scope')));
 value:=data.ddo_field(component,'effective_version');
 IF coalesce(value,'["null"]')<>'["null"]'::jsonb THEN fields:=fields||jsonb_build_array(jsonb_build_array('effective_version',value)); END IF;
 RETURN ops.ddo_structural_merge(statement,ops.ddo_structural_map(jsonb_build_array(jsonb_build_array('definition_component',ops.ddo_structural_map(fields)))));
 END IF;
 component:=data.ddo_field(report,'condition_qualification');
 fields:=jsonb_build_array(jsonb_build_array('relation',data.ddo_field(component,'relation')));
 value:=data.ddo_field(component,'effective_version');
 IF coalesce(value->>1,'')<>'' THEN fields:=fields||jsonb_build_array(jsonb_build_array('effective_version',value)); END IF;
 FOREACH role_name IN ARRAY ARRAY['qualifier','host_predicate'] LOOP
 SELECT jsonb_build_array('sequence',coalesce(jsonb_agg(ops.ddo_structural_map(jsonb_build_array(
 jsonb_build_array('source_pointer',data.ddo_field(item,'source_pointer')),
 jsonb_build_array('passage',ops.ddo_structural_span(report,data.ddo_field(item,'span'))))) ORDER BY ordinal),'[]')) INTO citations
 FROM jsonb_array_elements(data.ddo_field(component,role_name)->1) WITH ORDINALITY selected(item,ordinal);
 fields:=fields||jsonb_build_array(jsonb_build_array(role_name,citations));
 END LOOP;
 RETURN ops.ddo_structural_merge(statement,ops.ddo_structural_map(jsonb_build_array(jsonb_build_array('condition_qualification',ops.ddo_structural_map(fields)))));
END $structural$;

REVOKE ALL ON FUNCTION ops.ddo_structural_map(jsonb),ops.ddo_structural_pick(jsonb,text[],boolean),
ops.ddo_structural_merge(jsonb,jsonb),ops.ddo_structural_citation(jsonb,text),ops.ddo_structural_span(jsonb,jsonb),
ops.ddo_structural_citations(jsonb,jsonb),ops.ddo_structural_clause_field(jsonb,jsonb),ops.ddo_structural_comparison_statement(jsonb),ops.ddo_structural_statement(jsonb,text) FROM PUBLIC;
"""


def structural_admission_native_sql():
    import json
    from dataclasses import asdict

    from .declared_structural_admission import (
        ADMISSION_EFFECT,
        ADMISSION_FACTORY,
        ADMISSION_KIND,
        ADMISSION_OPERATION,
        REFERENCE_KIND,
        STRUCTURAL_REPORT_PRODUCERS,
        DdoStructuralAdmission,
    )

    fields = {
        "version",
        "report",
        "component_id",
        "policy_id",
        "policy_version",
        "statement_encoding",
        "statement_meaning_json",
        "standing",
        "assessment_basis",
        "scientific_truth",
        "member_truth",
    }
    if fields != DdoStructuralAdmission.model_fields.keys():
        raise ValueError("native structural disclosure must cover its exact public contract")
    sql = r"""
CREATE OR REPLACE FUNCTION ops.ddo_structural_command_eligible(definition sem.data_operation_definition)
RETURNS boolean LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $structural$
 SELECT definition.operation_id='__OPERATION__' AND definition.profile='command'
 AND definition.support_contract->'capabilities'->>'preparation'='native-publication'
 AND definition.support_contract->'capabilities'->'forms'='["scalar"]'::jsonb
 AND definition.support_contract->'capabilities'->'prepared_factory'->>'entrypoint'='__FACTORY__'
 AND definition.support_contract->'effects'='__EFFECTS__'::jsonb
 AND definition.support_contract->'capabilities'->'prepared_factory'->>'source_digest' ~ '^[0-9a-f]{64}$'
 AND definition.implementation_revision LIKE 'implementation-slice:%'
$structural$;

CREATE OR REPLACE FUNCTION ops.ddo_structural_product_reference(product kb.data_product) RETURNS jsonb
LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $structural$
 SELECT jsonb_build_object('product_id',(product).id,'member_id',NULL,'kind_contract',(product).kind_contract,
 'project_id',(product).project_id,'subject',(product).subject,'subject_definition',(product).subject_definition,
 'original_source',(product).original_source,'analyzed_scope_meaning',data.canonical_json(data.ddo_json_meaning((product).analyzed_scope)))
$structural$;

CREATE OR REPLACE FUNCTION ops.ddo_require_structural_admission_completion(r ops.data_request,completion jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $structural$
DECLARE definition sem.data_operation_definition; selected jsonb; output jsonb; report_product kb.data_product;
 pass_product kb.data_product; pass_kind sem.data_kind_contract; admitted ops.original_source_admission;
 pass_body jsonb; frame jsonb; passes jsonb:='{}'; actors jsonb:='[]'; parent_values jsonb:='[]'; c jsonb;
 report jsonb; statement jsonb; expected jsonb; selected_case jsonb; report_reference jsonb; producer_count bigint;
 report_kind text; variant text; report_role text; policy_id text; selected_component text;
BEGIN
 SELECT * INTO STRICT definition FROM sem.data_operation_definition WHERE release_id=r.release_id AND operation_id=r.operation_id;
 IF NOT coalesce((definition.command_class=\'structural\'),false) THEN
 IF definition.operation_id='__OPERATION__' OR EXISTS(SELECT FROM jsonb_array_elements(definition.support_contract->'effects') effect
 WHERE effect->>'name'='native-evaluator-structural-admission') THEN
 RAISE EXCEPTION 'structural admission requires its exact command/effect/factory' USING ERRCODE='23514'; END IF;
 RETURN; END IF;
 IF NOT pg_has_role(coalesce(nullif(current_setting('role'),'none'),session_user),'corpus_sem_evaluator','MEMBER') THEN
 RAISE EXCEPTION 'structural admission requires native evaluator purpose' USING ERRCODE='42501'; END IF;
 IF completion->>'outcome' IS DISTINCT FROM 'success' OR jsonb_array_length(completion->'inputs')<>4
 OR jsonb_array_length(completion->'outputs')<>1 THEN
 RAISE EXCEPTION 'structural admission requires one report, three exact passes and one conclusion' USING ERRCODE='23514'; END IF;
 SELECT value INTO STRICT selected FROM jsonb_array_elements(completion->'inputs') WHERE value->>'role' IN ('comparison','condition','definition');
 IF selected->>'member_id' IS NOT NULL OR (selected->>'position')::integer IS DISTINCT FROM 0
 OR (selected->>'multiplicity')::integer IS DISTINCT FROM 1 THEN
 RAISE EXCEPTION 'structural report must be its exact whole scalar input' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT report_product FROM kb.data_product WHERE id=selected->>'product_id' AND project_id=r.project_id;
 SELECT kind.kind INTO STRICT report_kind FROM sem.data_kind_contract kind WHERE kind.kind_contract=report_product.kind_contract AND kind.universe='ordinary';
 CASE report_kind
 WHEN 'urn:corpus:structural:DeclaredComparisonReport' THEN variant:='qualified_comparison'; report_role:='comparison'; policy_id:='independent-structural-comparison-1';
 WHEN 'urn:corpus:structural:DeclaredConditionReport' THEN variant:='condition_qualification'; report_role:='condition'; policy_id:='independent-condition-qualification-1';
 WHEN 'urn:corpus:structural:DeclaredDefinitionComponentsReport' THEN variant:='definition_components'; report_role:='definition'; policy_id:='independent-definition-component-1';
 ELSE RAISE EXCEPTION 'structural admission requires its actual released report kind' USING ERRCODE='23514'; END CASE;
 report:=data.ddo_json(report_product.canonical_body);
 IF report->>'kind' IS DISTINCT FROM variant OR selected->>'role' IS DISTINCT FROM report_role THEN
 RAISE EXCEPTION 'structural report differs from its exact choice-bound nominal variant' USING ERRCODE='23514'; END IF;
 SELECT count(*) INTO producer_count FROM ops.data_derivation episode
 JOIN ops.data_derivation_output produced ON produced.derivation_id=episode.id
 JOIN ops.data_publication_receipt receipt ON receipt.derivation_id=episode.id AND receipt.intent_id=episode.intent_id
 JOIN ops.data_request request ON request.id=episode.request_id
 JOIN sem.data_operation_definition owner ON owner.release_id=episode.release_id AND owner.operation_id=request.operation_id
 JOIN ops.data_completion_intent intent ON intent.id=episode.intent_id
 WHERE produced.product_id=report_product.id AND produced.member_id IS NULL AND produced.role='result'
 AND produced.position=0 AND produced.multiplicity=1 AND episode.outcome='success'
 AND owner.profile='derivation'
 AND owner.support_contract->'effects'='[]'::jsonb
 AND (variant,owner.operation_id,owner.support_contract->'capabilities'->'prepared_factory'->>'entrypoint') IN (
 __REPORT_PRODUCERS__)
 AND owner.support_contract->'capabilities'->'prepared_factory'->>'source_digest' ~ '^[0-9a-f]{64}$'
 AND owner.implementation_revision LIKE 'implementation-slice:%' AND owner.recipe=episode.recipe
 AND intent.payload->>'implementation_revision'=owner.implementation_revision
 AND jsonb_array_length(coalesce(intent.payload->'execution_evidence'->'cpu_receipts','[]'))=1
 AND EXISTS(SELECT FROM ops.ddo_input_support_refs(r.binding,selected) support
 WHERE support->>'kind'='computation' AND support->>'derivation_id'=episode.id);
 IF producer_count<>1 THEN RAISE EXCEPTION 'structural report lacks its one actual captured producer for the selected variant' USING ERRCODE='23514'; END IF;
 report_reference:=ops.ddo_structural_product_reference(report_product);
 FOR selected IN SELECT value FROM jsonb_array_elements(completion->'inputs') WHERE value->>'role'='passes' LOOP
 IF selected->>'member_id' IS NOT NULL OR (selected->>'multiplicity')::integer IS DISTINCT FROM 1 THEN
 RAISE EXCEPTION 'structural passes require distinct whole original authored products' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT pass_product FROM kb.data_product WHERE id=selected->>'product_id' AND project_id=r.project_id;
 SELECT * INTO STRICT pass_kind FROM sem.data_kind_contract WHERE kind_contract=pass_product.kind_contract;
 IF pass_kind.kind IS DISTINCT FROM '__REFERENCE_KIND__' OR pass_kind.universe IS DISTINCT FROM 'evaluator' THEN
 RAISE EXCEPTION 'structural pass differs from its protected nominal kind' USING ERRCODE='23514'; END IF;
 SELECT admission.* INTO STRICT admitted FROM ops.original_source_admission admission
 JOIN ops.ddo_input_support_refs(r.binding,selected) support
 ON support->>'kind'='authored' AND support->>'admission_id'=admission.id AND support->>'source_reference'=admission.source_reference
 WHERE admission.product_id=pass_product.id AND admission.project_id=r.project_id
 AND admission.reference->>'kind'='authored-fact' AND ops.ddo_original_admission_valid(admission);
 pass_body:=data.ddo_json(pass_product.canonical_body);
 IF admitted.evidence->>'standing' IS DISTINCT FROM 'authored' OR nullif(admitted.evidence->>'submitted_by','') IS NULL
 OR admitted.reference->>'author' IS DISTINCT FROM pass_body->>'author_assertion'
 OR admitted.evidence->>'author_assertion' IS DISTINCT FROM pass_body->>'author_assertion'
 OR pass_body->'actor'->>'principal' IS DISTINCT FROM pass_body->>'author_assertion'
 OR pass_body->'actor'->>'basis' IS DISTINCT FROM 'authored_attribution'
 OR pass_body->>'version' IS DISTINCT FROM 'structural-reference-pass-1' OR pass_body->>'pass_kind' NOT IN ('A','B','C')
 OR passes ? (pass_body->>'pass_kind') THEN
 RAISE EXCEPTION 'structural pass lacks its exact original submitted author attribution' USING ERRCODE='23514'; END IF;
 IF frame IS NULL THEN frame:=pass_body->'frame'; END IF;
 IF frame IS DISTINCT FROM pass_body->'frame' OR jsonb_strip_nulls(frame->'report') IS DISTINCT FROM jsonb_strip_nulls(report_reference)
 OR jsonb_strip_nulls(frame->'inputs') IS DISTINCT FROM jsonb_strip_nulls(report->'inputs')
 OR frame->>'question' IS DISTINCT FROM report->'inputs'->>'question'
 OR jsonb_array_length(pass_body->'cases')<>1 OR pass_body->'cases'->0->>'case_id' IS DISTINCT FROM frame->>'case_id'
 OR frame->>'operation' IS DISTINCT FROM variant OR frame->>'rubric_version' IS DISTINCT FROM policy_id
 OR NOT frame ? 'component_id' OR ((frame->>'component_id' IS NOT NULL) IS DISTINCT FROM (variant='definition_components'))
 OR frame->>'direction' NOT IN ('source_first','output_first')
 OR (frame->>'direction'='source_first' AND frame->'exposed_outputs'<>'[]'::jsonb)
 OR (frame->>'direction'='output_first' AND NOT EXISTS(SELECT FROM jsonb_array_elements(frame->'exposed_outputs') exposed
 WHERE jsonb_strip_nulls(exposed)=jsonb_strip_nulls(report_reference))) THEN
 RAISE EXCEPTION 'structural passes differ from exact report/source/question/rubric/exposure frame' USING ERRCODE='23514'; END IF;
 IF actors @> jsonb_build_array(pass_body->'actor') THEN
 RAISE EXCEPTION 'structural passes repeat an attributed actor identity' USING ERRCODE='23514'; END IF;
 actors:=actors||jsonb_build_array(pass_body->'actor');
 IF pass_body->>'pass_kind' IN ('A','B') THEN
 IF pass_body->'parents'<>'[]'::jsonb THEN RAISE EXCEPTION 'A/B cannot adjudicate another pass' USING ERRCODE='23514'; END IF;
 parent_values:=parent_values||jsonb_build_array(jsonb_build_object('reference',ops.ddo_structural_product_reference(pass_product),'body_digest',pass_product.body_digest)); END IF;
 passes:=passes||jsonb_build_object(pass_body->>'pass_kind',pass_body);
 END LOOP;
 IF (SELECT count(*) FROM jsonb_object_keys(passes))<>3 OR NOT passes ?& ARRAY['A','B','C'] THEN
 RAISE EXCEPTION 'structural admission requires the exact A/B/C population' USING ERRCODE='23514'; END IF;
 c:=passes->'C';
 IF jsonb_array_length(c->'parents')<>2 OR jsonb_strip_nulls(c->'parents') @> jsonb_strip_nulls(parent_values) IS NOT TRUE
 OR jsonb_strip_nulls(parent_values) @> jsonb_strip_nulls(c->'parents') IS NOT TRUE THEN
 RAISE EXCEPTION 'C does not adjudicate exact original A/B product/body identities' USING ERRCODE='23514'; END IF;
 selected_component:=frame->>'component_id';
 statement:=ops.ddo_structural_statement(report_product.canonical_body,selected_component);
 SELECT value INTO STRICT selected_case FROM jsonb_array_elements(c->'cases')
 WHERE value->>'facet'='public_statement' AND value->'path'='["public_statement"]'::jsonb
 AND value->>'judgment'='supported' AND value->>'expected_meaning_json'=data.canonical_json(statement);
 IF NOT (selected_case->'source_passages' @> coalesce((SELECT jsonb_agg(value->>'passage_id') FROM jsonb_array_elements(report->'inputs'->'passages')),'[]')) THEN
 RAISE EXCEPTION 'structural supported statement omits selected source passages' USING ERRCODE='23514'; END IF;
 expected:=jsonb_build_object('version','structural-admission-1','report',report_reference,'component_id',selected_component,
 'policy_id',policy_id,'policy_version','1','statement_encoding','ddo-semantic-value-v1',
 'statement_meaning_json',data.canonical_json(statement),'standing','admitted_structural_statement',
 'assessment_basis','independently_attributed_authored_judgments','scientific_truth','not_established',
 'member_truth','not_established_by_assembly_admission');
 output:=completion->'outputs'->0;
 IF output->>'role' IS DISTINCT FROM 'admission' OR output->>'member_id' IS NOT NULL
 OR (output->>'position')::integer IS DISTINCT FROM 0 OR (output->>'multiplicity')::integer IS DISTINCT FROM 1
 OR output->'product'->'members' IS DISTINCT FROM '[]'::jsonb
 OR NOT EXISTS(SELECT FROM sem.data_kind_contract kind WHERE kind.kind_contract=output->'product'->>'kind_contract'
 AND kind.kind='__KIND__' AND kind.universe='ordinary')
 OR data.ddo_normalize(output->'product'->'body') IS DISTINCT FROM data.ddo_normalize(data.ddo_json_meaning(expected)) THEN
 RAISE EXCEPTION 'structural ordinary conclusion differs from exact independently adjudicated statement' USING ERRCODE='23514'; END IF;
EXCEPTION WHEN no_data_found OR too_many_rows THEN
 RAISE EXCEPTION 'structural admission cannot resolve exact original custody' USING ERRCODE='23514';
END $structural$;

REVOKE ALL ON FUNCTION ops.ddo_structural_command_eligible(sem.data_operation_definition),
ops.ddo_structural_product_reference(kb.data_product),ops.ddo_require_structural_admission_completion(ops.data_request,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.ddo_require_structural_dossier_completion(r ops.data_request,completion jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $structural$
DECLARE definition sem.data_operation_definition; selected jsonb; conclusion kb.data_product;
 comparison_product kb.data_product; admission_value jsonb; actual_count bigint;
BEGIN
 IF r.operation_id<>'structure.dossier/declared' THEN RETURN; END IF;
 SELECT * INTO STRICT definition FROM sem.data_operation_definition WHERE release_id=r.release_id AND operation_id=r.operation_id;
 IF definition.profile IS DISTINCT FROM 'derivation' OR definition.support_contract->'effects' IS DISTINCT FROM '[]'::jsonb
 OR definition.support_contract->'capabilities'->'prepared_factory'->>'entrypoint' IS DISTINCT FROM 'corpus_structure.methods.dossier_declared.DossierOperation.acquire_port'
 OR (definition.support_contract->'capabilities'->'prepared_factory'->>'source_digest' ~ '^[0-9a-f]{64}$') IS NOT TRUE
 OR (definition.implementation_revision LIKE 'implementation-slice:%') IS NOT TRUE THEN
 RAISE EXCEPTION 'structural dossier requires its actual captured preparation factory' USING ERRCODE='23514'; END IF;
 FOR selected IN SELECT item FROM jsonb_array_elements(completion->'inputs') item WHERE item->>'role'='admissions' LOOP
 IF selected->>'member_id' IS NOT NULL OR (selected->>'multiplicity')::integer IS DISTINCT FROM 1 THEN
 RAISE EXCEPTION 'dossier admission requires an exact whole conclusion' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT conclusion FROM kb.data_product WHERE id=selected->>'product_id' AND project_id=r.project_id;
 IF NOT EXISTS(SELECT FROM sem.data_kind_contract kind WHERE kind.kind_contract=conclusion.kind_contract
 AND kind.kind='__KIND__' AND kind.universe='ordinary') THEN
 RAISE EXCEPTION 'dossier admission differs from its actual ordinary structural kind' USING ERRCODE='23514'; END IF;
 -- Ordinary consumption proves the issuer's committed common receipt and exact
 -- output. It never reads protected pass bodies or invokes evaluator issuance.
 -- The enclosing common support guard authenticates use visibility, locks and
 -- full protected revocation closure, including direct issuer revocation.
 SELECT count(*) INTO actual_count FROM ops.data_derivation episode
 JOIN ops.data_derivation_output output ON output.derivation_id=episode.id
 JOIN ops.data_publication_receipt receipt ON receipt.derivation_id=episode.id AND receipt.intent_id=episode.intent_id
 JOIN ops.data_completion_intent intent ON intent.id=episode.intent_id
 JOIN ops.data_request request ON request.id=episode.request_id
 JOIN sem.data_operation_definition issuer ON issuer.release_id=episode.release_id AND issuer.operation_id=request.operation_id
 WHERE output.product_id=conclusion.id AND output.member_id IS NULL AND output.role='admission'
 AND output.position=0 AND output.multiplicity=1 AND episode.outcome='success'
 AND (issuer.command_class=\'structural\') AND episode.recipe=issuer.recipe
 AND intent.payload->>'implementation_revision'=issuer.implementation_revision
 AND (SELECT count(*) FROM ops.data_derivation_output other WHERE other.derivation_id=episode.id)=1
 AND data.ddo_normalize(intent.payload->'outputs'->0->'product'->'body')=conclusion.canonical_body
 AND EXISTS(SELECT FROM ops.ddo_input_support_refs(r.binding,selected) support
 WHERE support->>'kind'='computation' AND support->>'derivation_id'=episode.id);
 IF actual_count<>1 THEN RAISE EXCEPTION 'dossier admission lacks its exact actual native issuer receipt' USING ERRCODE='23514'; END IF;
 admission_value:=data.ddo_json(conclusion.canonical_body);
 SELECT product.* INTO STRICT comparison_product FROM kb.data_product product
 JOIN jsonb_array_elements(completion->'inputs') input ON input->>'product_id'=product.id
 WHERE input->>'role'='comparisons' AND input->>'member_id' IS NULL
 AND product.id=admission_value->'report'->>'product_id' AND product.project_id=r.project_id;
 IF jsonb_strip_nulls(admission_value->'report') IS DISTINCT FROM jsonb_strip_nulls(ops.ddo_structural_product_reference(comparison_product))
 OR admission_value->>'statement_encoding' IS DISTINCT FROM 'ddo-semantic-value-v1'
 OR admission_value->>'statement_meaning_json' IS DISTINCT FROM data.canonical_json(ops.ddo_structural_comparison_statement(comparison_product.canonical_body)) THEN
 RAISE EXCEPTION 'dossier admission differs from the actual retained comparison and exact statement' USING ERRCODE='23514'; END IF;
 END LOOP;
EXCEPTION WHEN no_data_found OR too_many_rows THEN
 RAISE EXCEPTION 'dossier admission cannot resolve exact ordinary issuer/report custody' USING ERRCODE='23514';
END $structural$;
REVOKE ALL ON FUNCTION ops.ddo_require_structural_dossier_completion(ops.data_request,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.ddo_structural_report_support(selected_use text,read_id text,requested_products jsonb) RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $structural$
DECLARE boundary ops.data_demand_read; demand ops.data_demand; chosen ops.demand_use; episode ops.data_derivation;
 issuer sem.data_operation_definition; conclusion kb.data_product; report kb.data_product;
 input ops.data_derivation_input; report_use ops.demand_use; support ops.data_derivation_support;
 value jsonb; role_name text; nominal text;
BEGIN
 -- This is one selectively disclosed ordinary edge, not traversal of an issuer's
 -- protected request, frame, actors or original A/B/C inputs.
 IF jsonb_typeof(requested_products) IS DISTINCT FROM 'array' THEN RETURN NULL; END IF;
 SELECT * INTO STRICT boundary FROM ops.data_demand_read WHERE id=read_id;
 SELECT * INTO STRICT demand FROM ops.data_demand WHERE id=boundary.demand_id;
 SELECT * INTO STRICT chosen FROM ops.demand_use WHERE id=selected_use AND demand_id=boundary.demand_id;
 IF chosen.fate IS DISTINCT FROM 'fulfilled' OR NOT coalesce(ops.ddo_read_visible(chosen.created_at,chosen.created_xid,boundary),false)
 OR NOT coalesce(ops.ddo_use_valid(chosen,boundary),false) OR EXISTS(SELECT FROM ops.demand_use newer
 WHERE newer.obligation_id=chosen.obligation_id AND ops.ddo_read_visible(newer.created_at,newer.created_xid,boundary)
 AND (newer.created_at,newer.id)>(chosen.created_at,chosen.id)) THEN RETURN NULL; END IF;
 SELECT * INTO STRICT episode FROM ops.data_derivation WHERE id=chosen.derivation_id AND outcome='success';
 SELECT definition.* INTO STRICT issuer FROM sem.data_operation_definition definition
 JOIN ops.data_request request ON request.operation_id=definition.operation_id AND definition.release_id=episode.release_id
 WHERE request.id=episode.request_id AND request.project_id=demand.project_id;
 IF NOT coalesce((issuer.command_class=\'structural\'),false)
 OR NOT coalesce(ops.ddo_policy_authority_leaf(episode.id),false) THEN RETURN NULL; END IF;
 SELECT product.* INTO STRICT conclusion FROM ops.data_derivation_output output
 JOIN kb.data_product product ON product.id=output.product_id
 JOIN sem.data_kind_contract kind ON kind.kind_contract=product.kind_contract
 WHERE output.derivation_id=episode.id AND output.role='admission' AND output.position=0
 AND output.multiplicity=1 AND output.member_id IS NULL AND product.project_id=demand.project_id
 AND kind.kind='__KIND__' AND kind.universe='ordinary' AND requested_products ? product.id;
 value:=data.ddo_json(conclusion.canonical_body);
 CASE value->>'policy_id'
 WHEN 'independent-structural-comparison-1' THEN role_name:='comparison'; nominal:='urn:corpus:structural:DeclaredComparisonReport';
 WHEN 'independent-condition-qualification-1' THEN role_name:='condition'; nominal:='urn:corpus:structural:DeclaredConditionReport';
 WHEN 'independent-definition-component-1' THEN role_name:='definition'; nominal:='urn:corpus:structural:DeclaredDefinitionComponentsReport';
 ELSE RETURN NULL; END CASE;
 SELECT * INTO STRICT input FROM ops.data_derivation_input WHERE derivation_id=episode.id AND role=role_name
 AND position=0 AND multiplicity=1 AND member_id IS NULL;
 SELECT product.* INTO STRICT report FROM kb.data_product product
 JOIN sem.data_kind_contract kind ON kind.kind_contract=product.kind_contract
 WHERE product.id=input.product_id AND product.project_id=demand.project_id
 AND kind.kind=nominal AND kind.universe='ordinary' AND requested_products ? product.id
 AND ops.ddo_body_access(product.kind_contract,product.canonical_body);
 IF jsonb_strip_nulls(value->'report') IS DISTINCT FROM jsonb_strip_nulls(ops.ddo_structural_product_reference(report)) THEN RETURN NULL; END IF;
 -- The consumed original support row fixes the report's actual prior use and
 -- episode; a same-shaped product or an arbitrary historical use is insufficient.
 SELECT original.* INTO STRICT support FROM ops.data_derivation_support original
 WHERE original.derivation_id=episode.id AND original.role=role_name AND original.position=0;
 SELECT used.* INTO STRICT report_use FROM ops.demand_use used
 JOIN ops.data_derivation producer ON producer.id=used.derivation_id
 JOIN ops.data_request request ON request.id=producer.request_id
 JOIN ops.data_derivation_output output ON output.derivation_id=producer.id
 WHERE used.id=support.admission_use_id AND used.derivation_id=support.support_derivation_id
 AND used.fate='fulfilled' AND producer.outcome='success' AND producer.completed_at<=boundary.frontier_at
 AND request.project_id=demand.project_id AND output.product_id=report.id AND output.member_id IS NULL
 AND output.role='result' AND output.position=0 AND output.multiplicity=1
 AND ops.ddo_read_visible(used.created_at,used.created_xid,boundary) AND ops.ddo_use_valid(used,boundary);
 RETURN jsonb_build_object('product_id',report.id,'derivation_id',report_use.derivation_id,'use_id',report_use.id);
EXCEPTION WHEN no_data_found OR too_many_rows THEN RETURN NULL;
END $structural$;
REVOKE ALL ON FUNCTION ops.ddo_structural_report_support(text,text,jsonb) FROM PUBLIC;
"""
    sql = (
        sql.replace("__OPERATION__", ADMISSION_OPERATION)
        .replace("__FACTORY__", ADMISSION_FACTORY)
        .replace("__KIND__", ADMISSION_KIND)
        .replace("__REFERENCE_KIND__", REFERENCE_KIND)
        .replace(
            "__REPORT_PRODUCERS__",
            ",".join(
                "(" + ",".join("'" + item + "'" for item in (variant, operation, factory)) + ")"
                for variant, producers in STRUCTURAL_REPORT_PRODUCERS.items()
                for operation, factory in producers
            ),
        )
        .replace("__EFFECTS__", json.dumps([asdict(ADMISSION_EFFECT)], separators=(",", ":")))
    )
    return structural_statement_native_sql() + sql
