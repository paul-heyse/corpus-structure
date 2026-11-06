"""Prepare exact production/test diff in evidence only. Does not apply it or access DB."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=Path.cwd()
SQL=Path('python/corpus-structure/src/corpus_structure/semantic/sql/structural_products.sql')
TEST=Path('python/corpus-structure/tests/semantic/test_artifact_identity_native.py')
NEW=Path('python/corpus-structure/tests/semantic/test_artifact_identity_registered_native.py')
old_sql=(ROOT/SQL).read_text()
start=old_sql.index('CREATE OR REPLACE FUNCTION ops.validate_artifact_identity(')
end=old_sql.index('REVOKE ALL ON FUNCTION ops.validate_artifact_identity',start)
body=old_sql[start:end]
body=body.replace(' field_ jsonb; expected_value double precision; model_id text; expected_provenance jsonb; unbound jsonb; anchors jsonb;',' field_ jsonb; expected_value double precision; model_id text; expected_provenance jsonb; unbound jsonb; anchors jsonb;\n parameter_name text; parameter_value jsonb; parameter_text text; decoded_value double precision;\n title_threshold double precision; config_policy jsonb:=\'{}\';')
old=''' policy:=product->'policy';
 IF product->>'identity_grain' IS DISTINCT FROM 'source_work_artifact_lineage'
  OR jsonb_typeof(config->'title_threshold') IS DISTINCT FROM 'number'
  OR (config->>'title_threshold')::double precision<0 OR (config->>'title_threshold')::double precision>100'''
new=''' policy:=product->'policy';
 -- MethodRegistry stores floats as canonical decimal strings; products keep typed numbers.
 -- Decode only these declared numeric configuration fields, without rewriting custody bytes.
 IF jsonb_typeof(config->'policy') IS DISTINCT FROM 'object'
  OR jsonb_typeof(policy) IS DISTINCT FROM 'object' THEN
  RAISE EXCEPTION 'artifact model requires five strict finite probabilities and exact custody' USING ERRCODE='23514'; END IF;
 IF NOT ((config->'policy') ?& ARRAY['prior','code_m','code_u','title_m','title_u'])
  OR (SELECT count(*) FROM jsonb_each(config->'policy'))<>5 THEN
  RAISE EXCEPTION 'artifact model requires five strict finite probabilities and exact custody' USING ERRCODE='23514'; END IF;
 FOR parameter_name,parameter_value IN
  SELECT key,value FROM jsonb_each(config->'policy')
  UNION ALL SELECT 'title_threshold',config->'title_threshold' LOOP
  IF COALESCE(jsonb_typeof(parameter_value),'null') NOT IN ('number','string') THEN
   RAISE EXCEPTION 'artifact numeric config requires finite typed values' USING ERRCODE='23514'; END IF;
  parameter_text:=parameter_value#>>'{}';
  IF jsonb_typeof(parameter_value)='string' THEN
   -- Canonical floats have no exponent; reject it before the decimal normalizer expands it.
   IF parameter_text ~ '[eE]' THEN
    RAISE EXCEPTION 'artifact numeric config requires canonical decimal strings' USING ERRCODE='23514'; END IF;
   IF parameter_text IS DISTINCT FROM data.decimal_canonical(parameter_text) THEN
    RAISE EXCEPTION 'artifact numeric config requires canonical decimal strings' USING ERRCODE='23514'; END IF;
  END IF;
  decoded_value:=parameter_text::double precision;
  IF NOT (decoded_value>'-Infinity'::double precision AND decoded_value<'Infinity'::double precision) THEN
   RAISE EXCEPTION 'artifact numeric config requires finite typed values' USING ERRCODE='23514'; END IF;
  IF parameter_name='title_threshold' THEN
   IF decoded_value<0 OR decoded_value>100 THEN
    RAISE EXCEPTION 'artifact title threshold must be between zero and one hundred' USING ERRCODE='23514'; END IF;
   title_threshold:=decoded_value;
  ELSE
   IF decoded_value<=0 OR decoded_value>=1 THEN
    RAISE EXCEPTION 'artifact model requires five strict finite probabilities and exact custody' USING ERRCODE='23514'; END IF;
   config_policy:=config_policy||jsonb_build_object(parameter_name,decoded_value);
  END IF;
 END LOOP;
 IF product->>'identity_grain' IS DISTINCT FROM 'source_work_artifact_lineage' '''
assert old in body
body=body.replace(old,new.rstrip())
body=body.replace("policy IS DISTINCT FROM config->'policy'",'policy IS DISTINCT FROM config_policy')
body=body.replace("lexical*100 >=(config->>'title_threshold')::double precision",'lexical*100 >=title_threshold')
old_exception="EXCEPTION WHEN no_data_found OR too_many_rows THEN\n RAISE EXCEPTION 'artifact candidate or source custody cannot resolve exact population' USING ERRCODE='23514';"
new_exception=old_exception+"\nWHEN invalid_text_representation OR numeric_value_out_of_range THEN\n RAISE EXCEPTION 'artifact numeric config requires finite typed values' USING ERRCODE='23514';"
assert old_exception in body
body=body.replace(old_exception,new_exception)
new_sql=old_sql[:start]+body+old_sql[end:]
old_test=(ROOT/TEST).read_text()
needle='''        check(product)
        # Existing pair-only anchor/exclusion semantics are independently enforced natively.'''
replacement='''        check(product)
        # Ordinary registry ABI stores float config fields as canonical strings.
        # This helper still tests nonempty likelihood/routes independently of source custody.
        from corpus_structure.orchestrate.registry import canonical_numbers

        canonical_cfg = canonical_numbers(cfg)
        check(product, canonical_cfg)
        for invalid in (None, True, [], {}, "NaN", "Infinity", "-Infinity", "70.0", "7e1", " 70", "1" + "0" * 400, -0.1, 100.1):
            bad_cfg = deepcopy(canonical_cfg)
            bad_cfg["title_threshold"] = invalid
            with pytest.raises(DBAPIError) as refused, conn.begin_nested():
                check(product, bad_cfg)
            assert refused.value.orig.sqlstate == "23514"
        # A valid but different threshold must not authenticate this frozen pair/routes output.
        for threshold in ("0", "100"):
            bad_cfg = deepcopy(canonical_cfg)
            bad_cfg["title_threshold"] = threshold
            with pytest.raises(DBAPIError) as refused, conn.begin_nested():
                check(product, bad_cfg)
            assert refused.value.orig.sqlstate == "23514"
        for invalid in (None, True, [], "policy", {}, {**canonical_cfg["policy"], "extra": "0.1"}):
            bad_cfg = deepcopy(canonical_cfg)
            bad_cfg["policy"] = invalid
            with pytest.raises(DBAPIError) as refused, conn.begin_nested():
                check(product, bad_cfg)
            assert refused.value.orig.sqlstate == "23514"
        for key in canonical_cfg["policy"]:
            for invalid in (None, True, [], {}, "NaN", "Infinity", "-Infinity", "0", "1", "0.10", "1e-1", "1" + "0" * 400):
                bad_cfg = deepcopy(canonical_cfg)
                bad_cfg["policy"][key] = invalid
                with pytest.raises(DBAPIError) as refused, conn.begin_nested():
                    check(product, bad_cfg)
                assert refused.value.orig.sqlstate == "23514"
        for key in ("prior", "code_m", "code_u", "title_m", "title_u"):
            forged = deepcopy(product)
            forged["policy"][key] = 0.2
            with pytest.raises(DBAPIError) as refused, conn.begin_nested():
                check(forged, canonical_cfg)
            assert refused.value.orig.sqlstate == "23514"
        # Existing pair-only anchor/exclusion semantics are independently enforced natively.'''
assert needle in old_test
new_test=old_test.replace(needle,replacement)
new_registered=(HERE/'registered-native-test.proposed.py').read_text()
for content in (new_test,new_registered):ast.parse(content)
patch=''.join(difflib.unified_diff(old_sql.splitlines(True),new_sql.splitlines(True),fromfile='a/'+str(SQL),tofile='b/'+str(SQL)))
patch+=''.join(difflib.unified_diff(old_test.splitlines(True),new_test.splitlines(True),fromfile='a/'+str(TEST),tofile='b/'+str(TEST)))
patch+=''.join(difflib.unified_diff([],new_registered.splitlines(True),fromfile='/dev/null',tofile='b/'+str(NEW)))
(HERE/'artifact-config-abi.patch').write_text(patch)
(HERE/'validate_artifact_identity.proposed.sql').write_text(body)
manifest={'outcome':'passed','production_edits':'not_applied','database_writes':'not_run','base_files':[{'path':str(p),'sha256':hashlib.sha256((ROOT/p).read_bytes()).hexdigest()} for p in [SQL,TEST]],'patch_sha256':hashlib.sha256(patch.encode()).hexdigest(),'new_test_destination':str(NEW),'checks':'Exact source replacements found; proposed Python test modules parsed. SQL/native integration tests not run because patch unapplied and database writes unauthorized.'}
(HERE/'patch-preparation.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
