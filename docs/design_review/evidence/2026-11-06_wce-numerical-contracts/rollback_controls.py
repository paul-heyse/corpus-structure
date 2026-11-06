"""Compile owned SQL and exercise its exact numerical block in a rollback-only scope."""

from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.methods.record_readings import _sealed_value
from corpus_structure.evaluate.operation_fitting import OperationEventFrame, OperationEventObservation, fit_operation_event
from corpus_structure.semantic import record_interpretation as ri
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings


def main():
    root = Path(__file__).resolve().parents[4]
    source = root / "python/corpus-structure/src/corpus_structure/semantic/sql"
    local_sql = (source / "source_contributions.sql").read_text()
    start = local_sql.index("    DECLARE axes_")
    end = local_sql.index("\n    END;\n   END IF;", start) + len("\n    END;")
    wrapper = "CREATE FUNCTION pg_temp.check_local_values(local_request jsonb,local_result jsonb) RETURNS void LANGUAGE plpgsql AS $$ BEGIN\n" + local_sql[start:end] + "\nEND $$"
    request = ri.LocalInterpretationRequest(
        decisions=(ri.Decision("role", (ri.Candidate("actor"), ri.Candidate("object"))),),
        potentials=(ri.LogPotential("evidence", ("role",), (-100.,-101.), ("source",)),),
        constraints=(),
        dependencies=tuple(ri.Dependency(k,v,"1") for k,v in (("source",ri.DependencyKind.OBSERVATION),("model",ri.DependencyKind.MODEL),("ontology",ri.DependencyKind.ONTOLOGY),("policy",ri.DependencyKind.POLICY))),
        selection=ri.CandidateSelection("q",("source",)),
        model_dependency_id="model",ontology_dependency_id="ontology",policy_dependency_id="policy",
        events=(ri.CompositeEvent("actor","actor role",((ri.Choice("role","actor"),),)),),
        limits=ri.SearchLimits(displayed_alternatives=1),
    )
    query = json.loads(json.dumps(_sealed_value(asdict(request))))
    result = json.loads(json.dumps(_sealed_value(asdict(ri.interpret_local(request)))))
    cases = []
    for field,value in (("probability",2),("decision","foreign"),("candidate","foreign"),("probability",0)):
        bad = deepcopy(result);bad["marginals"][0][field]=value;cases.append((query,bad))
    bad=deepcopy(result);bad["alternatives"][0]["choices"][0]["candidate"]="foreign";cases.append((query,bad))
    bad=deepcopy(result);bad["event_probabilities"][0]["event"]="foreign";cases.append((query,bad))
    bad=deepcopy(query);bad["potentials"][0]["values"].pop();cases.append((bad,result))
    fit_sql=(source/"operation_event_fitting.sql").read_text()
    fit_block=fit_sql[fit_sql.index(" parameters:=p_result->'parameters';"):fit_sql.index(" INSERT INTO eval.operation_event_fit(")]
    fit_wrapper="""CREATE FUNCTION pg_temp.check_fit_values(p_frame jsonb,p_result jsonb) RETURNS void LANGUAGE plpgsql AS $$
DECLARE frame_digest text:=encode(sha256(convert_to(data.canonical_json(ops.contextual_identity_value(p_frame->'frame')),'UTF8')),'hex');parameters jsonb;item jsonb;n integer;
BEGIN
"""+fit_block+"\nEND $$"
    fit_frame=OperationEventFrame(event_version="1",producer_version="1",rubric_digest="a"*64,reference_digest="b"*64,corpus_id="control",feature_names=("score",),event_ids=("0","1","2","3"),observations=tuple(OperationEventObservation(event_id=str(i),contribution_id="c"+str(i),source_ref="s",features=(score,),judgment="supported" if i>=2 else "unsupported") for i,score in enumerate((.1,.2,.8,.9))))
    native_frame=dict(frame=fit_frame.model_dump(mode="json"))
    fit_result=fit_operation_event(fit_frame).model_dump(mode="json")
    assert fit_result['status']=='fitted'
    bad_fits=[]
    for key in ("regularization_c","tolerance","max_iterations"):
        bad=deepcopy(fit_result);bad['parameters']['algorithm'][key]=None;bad_fits.append(bad)
    for key,value in (("prior_probability",2),("prior_probability",None),("fitted_probability",-1),("fitted_probability",None)):
        bad=deepcopy(fit_result);bad['predictions'][0][key]=value;bad_fits.append(bad)
    bad=deepcopy(fit_result);bad.update(status="failed",parameters=None);bad_fits.append(bad)
    rejected=fit_rejected=0
    with open_runtime_engine(Settings(),"numerical-contract-rollback",purpose="maintenance") as engine:
        with engine.connect() as conn:
            transaction=conn.begin()
            try:
                conn.exec_driver_sql(local_sql)
                conn.exec_driver_sql(fit_sql)
                conn.exec_driver_sql(wrapper)
                conn.exec_driver_sql(fit_wrapper)
                statement=text("SELECT pg_temp.check_local_values(CAST(:q AS jsonb),CAST(:r AS jsonb))")
                conn.execute(statement,dict(q=json.dumps(query),r=json.dumps(result)))
                for bad_query,bad_result in cases:
                    try:
                        with conn.begin_nested():
                            conn.execute(statement,dict(q=json.dumps(bad_query),r=json.dumps(bad_result)))
                    except DBAPIError:
                        rejected+=1
                    else:
                        raise AssertionError("malformed numerical product was admitted")
                fit_statement=text("SELECT pg_temp.check_fit_values(CAST(:f AS jsonb),CAST(:r AS jsonb))")
                conn.execute(fit_statement,dict(f=json.dumps(native_frame),r=json.dumps(fit_result)))
                for bad in bad_fits:
                    try:
                        with conn.begin_nested():conn.execute(fit_statement,dict(f=json.dumps(native_frame),r=json.dumps(bad)))
                    except DBAPIError:fit_rejected+=1
                    else:raise AssertionError("malformed fit product was admitted")
            finally:
                transaction.rollback()
    print(json.dumps(dict(outcome="passed",compiled_sql_files=2,valid_local_products=1,rejected_local_products=rejected,valid_fit_products=1,rejected_fit_products=fit_rejected,database_effects="rolled_back",scope="exact native numerical blocks; assembled admission/fitter tests not run")))


if __name__ == "__main__":
    main()
