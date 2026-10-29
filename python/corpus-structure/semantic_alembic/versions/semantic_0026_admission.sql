-- Frozen native enforcement descriptor, extracted from reviewed migration ASTs.
SET LOCAL ROLE corpus_sem_publisher;
ALTER FUNCTION data.publish_analysis_batch(text,text,text,bytea,bigint) RENAME TO publish_pre_execution_analysis_batch;
CREATE FUNCTION data.publish_analysis_batch(r text,z text,b text,p_content bytea,expected_revision bigint) RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $legacy$
BEGIN IF EXISTS(SELECT FROM sem.release WHERE release_id=r AND profile='semantic-2') THEN RAISE EXCEPTION 'composed analysis requires explicit derived intent' USING ERRCODE='23514'; END IF; RETURN data.publish_pre_execution_analysis_batch(r,z,b,p_content,expected_revision); END
$legacy$;
ALTER FUNCTION data.publish_analysis_batch(text,text,text,bytea,bigint) OWNER TO corpus_sem_publisher;
GRANT EXECUTE ON FUNCTION data.publish_analysis_batch(text,text,text,bytea,bigint) TO corpus_sem_writer;
SET LOCAL ROLE __MIGRATION_OWNER__;
CREATE FUNCTION data.execution_contract_descriptor() RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $descriptor$
 SELECT '{"functions":[{"body_sha256":"f2d0c8d51d35274329ed3bc55471a0912342702b6f4e6b661cc33697eb2ed398","config":["search_path=pg_catalog, pg_temp"],"execute_roles":["corpus_sem_reader","corpus_sem_writer"],"language":"sql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"text","security":false,"setof":false,"signature":"data.canonical_json(jsonb)","strict":true,"volatility":"i"},{"body_sha256":"fbb703c824379dfb9a12534359786680bdea7d5e19bfc6091f5f60fa20beeb87","config":["search_path=pg_catalog, pg_temp"],"execute_roles":["corpus_sem_reader","corpus_sem_writer"],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"text","security":false,"setof":false,"signature":"data.decimal_canonical(text)","strict":true,"volatility":"i"},{"body_sha256":"f857c8966b460a7ce3d30911dc361a68a470d1763cf0eb6de340bc4910bc10f3","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"integer","security":false,"setof":false,"signature":"data.compare_decimal(text,text)","strict":true,"volatility":"i"},{"body_sha256":"a7a2966fa904be812330f19dbdbe5c09d1a0e012881e918bd63d965f78cd903d","config":["search_path=pg_catalog, pg_temp"],"execute_roles":["corpus_sem_reader","corpus_sem_writer"],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"jsonb","security":false,"setof":false,"signature":"data.value_meaning(text,text,text,text[],boolean)","strict":false,"volatility":"s"},{"body_sha256":"14e142fe5990622f57dcfde26a507972595e3e6e2d2660f10456fb678b640e4b","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"boolean","security":false,"setof":false,"signature":"data.value_matches(text,text,text,text,boolean)","strict":false,"volatility":"s"},{"body_sha256":"e52d2960dc00bdb0fb5a3683be8f9657781846208c741771d297830cfc64cae4","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"sql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"text","security":false,"setof":false,"signature":"data.fact_identity(text,text,text,text,text,text)","strict":false,"volatility":"s"},{"body_sha256":"0052614a2653aab28f3ec73517636ff82a6ec9e8dcd01486e41b447db750e6e4","config":["search_path=pg_catalog, pg_temp"],"execute_roles":["corpus_sem_writer"],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"bigint","security":true,"setof":false,"signature":"ops.capture_cut(bigint,text,boolean)","strict":false,"volatility":"v"},{"body_sha256":"47c047a0acf683d8f93e281e6b25b642706e03cb4dfdc4974c9930f59f09f9e5","config":["search_path=pg_catalog, pg_temp"],"execute_roles":["corpus_sem_writer"],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"bigint","security":true,"setof":false,"signature":"ops.create_run(text,text,text,bigint,bytea,text,bigint,jsonb,text,text)","strict":false,"volatility":"v"},{"body_sha256":"5fa0ab774de951a5cf585aaaa16486ffd0281fe1962b96a5e09f290f21cc59e5","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"$migration_owner","parallel":"u","result":"trigger","security":false,"setof":false,"signature":"ops.check_source_scope()","strict":false,"volatility":"v"},{"body_sha256":"114f7e8df5ecb3b4c6c472d85e226ef10406fff757b195e7d48ad9d553217b8f","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"$migration_owner","parallel":"u","result":"trigger","security":false,"setof":false,"signature":"kb.check_offsets()","strict":false,"volatility":"v"},{"body_sha256":"ec9ec2eb64c1e5f7ad2269954f3bf98322f41ec2b33e96444973843a55faf797","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"trigger","security":true,"setof":false,"signature":"data.check_evidence_source()","strict":false,"volatility":"v"},{"body_sha256":"3b71d60c5db4cf31490641b4eeb9c07b7107f9c2d7b850c0844c9af69dbf0ced","config":["search_path=pg_catalog, pg_temp"],"execute_roles":["corpus_sem_reader","corpus_sem_writer"],"language":"sql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"text","security":true,"setof":true,"signature":"data.inference_seeds(text,text)","strict":false,"volatility":"s"},{"body_sha256":"35a09e0955a133b4446c58dfab97fabb427221ab82216896c81b1f2edf02b25a","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"void","security":false,"setof":false,"signature":"data.validate_pre_inference_state(text,text)","strict":false,"volatility":"s"},{"body_sha256":"93ff99e5d7e2b98cb14193d559af366e951f36dff4f03c06b3d1e0c44fbbbe8a","config":["search_path=pg_catalog, pg_temp"],"execute_roles":["corpus_sem_writer"],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"void","security":true,"setof":false,"signature":"data.begin_evaluation(bigint,text)","strict":false,"volatility":"v"},{"body_sha256":"f8c913b186501a374072888040e788eb9cf914704873fb48815ef1a8c0963e05","config":["search_path=pg_catalog, pg_temp"],"execute_roles":["corpus_sem_writer"],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"text","security":true,"setof":false,"signature":"data.initialize_source_project(text,text,text)","strict":false,"volatility":"v"},{"body_sha256":"c615dd98d22b35fcabce9484864f0a5ea150b68aa519f3501d6e7e67f1ce2640","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"trigger","security":true,"setof":false,"signature":"kb.record_observation_inputs()","strict":false,"volatility":"v"},{"body_sha256":"6c2ab3d4e5685ae38029ae89f506329ae2fc73cff3255e180abdb0c7280c45b6","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"trigger","security":false,"setof":false,"signature":"ops.guard_run_lifecycle()","strict":false,"volatility":"v"},{"body_sha256":"e01bad1a1678e90cf1588266fa2a68ddc9cc866e5490c3d1f93229647adf4752","config":["search_path=pg_catalog, pg_temp"],"execute_roles":["corpus_sem_writer"],"language":"sql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"boolean","security":true,"setof":false,"signature":"ops.valid_reuse(ops.task)","strict":false,"volatility":"s"},{"body_sha256":"254891b32e3a16a04f9a6dc7c057772013ad99d4e00392166b60c63ed64e6b93","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"$migration_owner","parallel":"u","result":"trigger","security":false,"setof":false,"signature":"ops.guard_task_lifecycle()","strict":false,"volatility":"v"},{"body_sha256":"e5a9c0c538b229ee594afb5f2c70394dd731c70b7585ce110ded88f28e4fede7","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"trigger","security":true,"setof":false,"signature":"ops.guard_cut_task()","strict":false,"volatility":"v"},{"body_sha256":"34b6b86a3a597e03286a2cf163a4d61892da3590327553227f51e2b77064881f","config":["search_path=pg_catalog, pg_temp"],"execute_roles":["corpus_sem_writer"],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"bigint","security":true,"setof":false,"signature":"ops.end_source_run(bigint,jsonb)","strict":false,"volatility":"v"},{"body_sha256":"c92f12f53e86cb8b81843188e95233df7a36792861b28b994c7156879ae9a762","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"sql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"jsonb","security":false,"setof":false,"signature":"data.report_field(jsonb,text)","strict":true,"volatility":"i"},{"body_sha256":"ffe3b493214fbe47b1f66a678acb28210d92d7210c8e3031722ef005f0e0d328","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"trigger","security":true,"setof":false,"signature":"data.check_entity_input()","strict":false,"volatility":"v"},{"body_sha256":"1f7df416a510f0a3eeeeabac938ba4c4d3426f08e3ee33d8075cad63b3a23ad2","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"void","security":true,"setof":false,"signature":"data.begin_pre_input_stage()","strict":false,"volatility":"v"},{"body_sha256":"d6626d045b4f856bba200d584b44291843d7b5ce5777de6e4c22e46f0395face","config":["search_path=pg_catalog, pg_temp"],"execute_roles":["corpus_sem_writer"],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"void","security":true,"setof":false,"signature":"data.begin_stage()","strict":false,"volatility":"v"},{"body_sha256":"7e07201933f4a12f0304362d450c36d049050f2915ee0bc81d91cfc6fa68be5d","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"void","security":true,"setof":false,"signature":"data.end_pre_input_stage()","strict":false,"volatility":"v"},{"body_sha256":"f2ab36833684637ae78bb620b6c7490246c85a1039797eb97a9438cfd9894ace","config":["search_path=pg_catalog, pg_temp"],"execute_roles":["corpus_sem_writer"],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"void","security":true,"setof":false,"signature":"data.end_stage()","strict":false,"volatility":"v"},{"body_sha256":"0995483d36f30734283b9db636b765b732b4ccbde28ab8d0307a105f7ac7e2be","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"trigger","security":true,"setof":false,"signature":"data.check_fact_input()","strict":false,"volatility":"v"},{"body_sha256":"ca834e5274323dedc1429b3b44e6eede6efe27b6644f658e7526a7bfd88c961e","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"$migration_owner","parallel":"u","result":"trigger","security":false,"setof":false,"signature":"ops.guard_source_selection()","strict":false,"volatility":"v"},{"body_sha256":"8dc36ba01023c34eb7a0d78bfee57abefae45e817b3c6059ff342be268bf550d","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"$migration_owner","parallel":"u","result":"trigger","security":false,"setof":false,"signature":"ops.guard_final_cut()","strict":false,"volatility":"v"},{"body_sha256":"69d460b42defac3ee67966b3993eae6fd7a2f0900decab024ed21d2cdfa8aa69","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"void","security":true,"setof":false,"signature":"data.validate_occurrence_context(text,text)","strict":false,"volatility":"s"},{"body_sha256":"f083be6143828f80f0082834cab93ca28134fac2705b39e484cc6bd1bd2e3ee8","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"void","security":true,"setof":false,"signature":"data.validate_entity_source(text,text)","strict":false,"volatility":"s"},{"body_sha256":"2edae1d809368c4ea81823168b183f237bd70c8eb5e07d5c899c602310522b4e","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"void","security":true,"setof":false,"signature":"data.finish_pre_context_evaluation(bigint,text,text)","strict":false,"volatility":"v"},{"body_sha256":"8b479173d0e1675634a18f1017eee2cbda67d5ae81ff4dd621f5628161c5c361","config":["search_path=pg_catalog, pg_temp"],"execute_roles":["corpus_sem_writer"],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"void","security":true,"setof":false,"signature":"ops.lock_input_snapshot(bigint)","strict":false,"volatility":"v"},{"body_sha256":"87c7f485ff9eadc2bf1c29272fe056fa30e6cfcb6ecbfea47ea47feb97429bf3","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"$migration_owner","parallel":"u","result":"trigger","security":false,"setof":false,"signature":"ops.guard_task_configuration()","strict":false,"volatility":"v"},{"body_sha256":"c3e11bbf59c5c081b1012219db932fd07caded97a1e95623002e34cfa99f8ecd","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"void","security":false,"setof":false,"signature":"data.validate_property_pre_fact_references(text,text,text,text,jsonb)","strict":false,"volatility":"s"},{"body_sha256":"f9c6b888956609c662ed7737bc4d1e96e0ac8175bfe278b86b99a667b6821f3c","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"void","security":false,"setof":false,"signature":"data.validate_property(text,text,text,text,jsonb)","strict":false,"volatility":"s"},{"body_sha256":"44112ecfe834287f2cf84abc00c5ce8390a081bb383033954c5ae72f277c6c6e","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"void","security":true,"setof":false,"signature":"data.finish_pre_source_identity_evaluation(bigint,text,text)","strict":false,"volatility":"v"},{"body_sha256":"1408f430e1f35c0e22c73046f1aafa74059c81fc7007e6c8cb893f6fa42cfec6","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"$migration_owner","parallel":"u","result":"trigger","security":false,"setof":false,"signature":"ops.guard_initial_task_error()","strict":false,"volatility":"v"},{"body_sha256":"f1bfa48131dde29bcafced9f6534e8809c57ad3a70bcb36cd01cb9b3250bec55","config":["search_path=pg_catalog, pg_temp"],"execute_roles":["corpus_sem_writer"],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"boolean","security":true,"setof":false,"signature":"ops.hold_agent_result(bigint,bigint,text,text,boolean,jsonb)","strict":false,"volatility":"v"},{"body_sha256":"9d86e9aa9fa64d3676d9688615f5a655e397233ee067b337462b31ee021a0d34","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"void","security":true,"setof":false,"signature":"data.validate_alternatives(text,text)","strict":false,"volatility":"s"},{"body_sha256":"5cdf7ab923dee4c36b93830f7837074fa498f6a3d6250d90de70a6bf151e83e1","config":["search_path=pg_catalog, pg_temp"],"execute_roles":["corpus_sem_reader","corpus_sem_writer"],"language":"sql","leakproof":false,"owner":"$migration_owner","parallel":"s","result":"boolean","security":false,"setof":false,"signature":"ops.execution_edge(text,text,text)","strict":false,"volatility":"i"},{"body_sha256":"932a4a926e1584cd2d6c88e8b3bb39fa7c7fb289bd07a7bd370570396dfd15e1","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"void","security":false,"setof":false,"signature":"data.validate_conditions(text,text)","strict":false,"volatility":"s"},{"body_sha256":"26f0ae4fe256e03b609a17ac6f76b3c9419e982a034de8bba6a482e1e5743d25","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"void","security":false,"setof":false,"signature":"data.validate_pre_contract_state(text,text)","strict":false,"volatility":"v"},{"body_sha256":"0c955c06b26f6f170313460b8272a741eab51b711a0afa8cb1cb7710fa879df3","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"void","security":false,"setof":false,"signature":"data.validate_state(text,text)","strict":false,"volatility":"s"},{"body_sha256":"57da2bc4da4a243575602d55dd41b994d690904fd514fea314acce5febc3a674","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"void","security":true,"setof":false,"signature":"data.finish_pre_contract_evaluation(bigint,text,text)","strict":false,"volatility":"v"},{"body_sha256":"83c40867998ecea83b6f0f3d3f975543b249c6f2a1d468049ea82e9cf22e28d2","config":["search_path=pg_catalog, pg_temp"],"execute_roles":["corpus_sem_writer"],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"void","security":true,"setof":false,"signature":"data.finish_evaluation(bigint,text,text)","strict":false,"volatility":"v"},{"body_sha256":"eb6c5d2548dc611ed218010191dd7426202b6b1ea0dfd28015f25698e2b0fdb1","config":["search_path=pg_catalog, pg_temp"],"execute_roles":["corpus_sem_writer"],"language":"sql","leakproof":false,"owner":"$migration_owner","parallel":"u","result":"text","security":false,"setof":false,"signature":"ops.execution_task_state(ops.task)","strict":false,"volatility":"s"},{"body_sha256":"5360cb07d0de8e4145edb1a653bcbcaf579d5e7d743ee483ab1912939b4fd097","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"$migration_owner","parallel":"u","result":"trigger","security":false,"setof":false,"signature":"ops.guard_execution_task()","strict":false,"volatility":"v"},{"body_sha256":"d6dd43868dc82882a53c95298708dbdb7a7bcd35acb4b542775cce4fae958c06","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"$migration_owner","parallel":"u","result":"trigger","security":false,"setof":false,"signature":"ops.guard_execution_run()","strict":false,"volatility":"v"},{"body_sha256":"59e17a68c818c97e6824ef1d315820d42263f6821e8d8ea0d22521750c7a0958","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"$migration_owner","parallel":"u","result":"trigger","security":false,"setof":false,"signature":"ops.require_completed_result()","strict":false,"volatility":"v"},{"body_sha256":"bb56745dab980d60990eea4ca7358ff8ea68c1149d0f25835426d9652bde5261","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"$migration_owner","parallel":"u","result":"trigger","security":false,"setof":false,"signature":"ops.guard_completed_result()","strict":false,"volatility":"v"},{"body_sha256":"acdc73e60981b8c8d3a55c085df5181a0a5536e103dddbe2772eb8353072179f","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"$migration_owner","parallel":"u","result":"trigger","security":false,"setof":false,"signature":"data.guard_completed_output()","strict":false,"volatility":"v"},{"body_sha256":"bef83475ec2379361d5e5224f0ea9cad28193431b31fb075e8f7628db2dd6649","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"bigint","security":true,"setof":false,"signature":"data.publish_contract_batch(text,text,text,bytea)","strict":false,"volatility":"v"},{"body_sha256":"74fe9c7f05f16d8424c287ee52c0550676387cce772970e6d9472d28d3ec6511","config":["search_path=pg_catalog, pg_temp"],"execute_roles":["corpus_sem_writer"],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"bigint","security":true,"setof":false,"signature":"data.publish_batch(text,text,text,bytea)","strict":false,"volatility":"v"},{"body_sha256":"e5ae360af2b9dfbdc4429b43d00c3ecbbaaa315719134d200bd16d4520858950","config":["search_path=pg_catalog, pg_temp"],"execute_roles":["corpus_sem_writer"],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"bigint","security":true,"setof":false,"signature":"data.publish_derived_batch(text,text,text,bytea,text,text,bigint,text,text,text)","strict":false,"volatility":"v"},{"body_sha256":"e3fe83da6d4256796bc2efdb73e126a98d496679c0f0e919f2295463db059511","config":["search_path=pg_catalog, pg_temp"],"execute_roles":["corpus_sem_writer"],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"void","security":true,"setof":false,"signature":"ops.renew_claim(bigint,bigint,text)","strict":false,"volatility":"v"},{"body_sha256":"1d844dd42b51f8fe201221b756ce25f3f5770c44c18a96967eb4009c32ffcf4e","config":["search_path=pg_catalog, pg_temp"],"execute_roles":["corpus_sem_writer"],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"void","security":true,"setof":false,"signature":"ops.release_claim(bigint,bigint,text,text)","strict":false,"volatility":"v"},{"body_sha256":"4ce6dcd6f401c833a26449bb15739153164a9977a81942ee119d1dbafdc90f63","config":["search_path=pg_catalog, pg_temp"],"execute_roles":["corpus_sem_writer"],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"jsonb","security":true,"setof":false,"signature":"ops.complete_task(bigint,bigint,text,jsonb,text,jsonb,jsonb)","strict":false,"volatility":"v"},{"body_sha256":"16f9990ed6caa38bd5324c5ae544e6a8c74205a6dfd6caf3e781bfab70a29328","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"$migration_owner","parallel":"u","result":"trigger","security":false,"setof":false,"signature":"ops.require_atomic_evaluation()","strict":false,"volatility":"v"},{"body_sha256":"a73f9e8b0098afbb16c9ccca717cb416dd632a013ed70bd3c85f005b6637e6f7","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"$migration_owner","parallel":"u","result":"trigger","security":false,"setof":false,"signature":"data.validate_assessment_counterpart()","strict":false,"volatility":"v"},{"body_sha256":"113f42e9cc5107ca5787085fd0b34551af2410f2f35226127d4619b55da6cf6f","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"trigger","security":true,"setof":false,"signature":"ops.validate_measurement_definition()","strict":false,"volatility":"v"},{"body_sha256":"53a83938cca645fe8de9a38e6f9d4abaaece50dcb320d82ff81ab8cc2109f01b","config":["search_path=pg_catalog, pg_temp","extra_float_digits=3"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"jsonb","security":false,"setof":false,"signature":"ops.decode_source_value(jsonb)","strict":false,"volatility":"i"},{"body_sha256":"99f1d2712e636b041eb29f6726051e617b60c62c52d3bc2985b97394cb3bf0d2","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"trigger","security":false,"setof":false,"signature":"ops.guard_measurement_custody()","strict":false,"volatility":"v"},{"body_sha256":"272c968d524001675ab06a70df69741e5e8aa2812e61c082cef59ae51eda27f2","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"trigger","security":true,"setof":false,"signature":"ops.materialize_source_measurements()","strict":false,"volatility":"v"},{"body_sha256":"1b1ca7d867ab79f50c725166f723a6e88dc5ad23f94930b6a4e9725f43751806","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"$migration_owner","parallel":"u","result":"trigger","security":false,"setof":false,"signature":"ops.guard_task_method_contract()","strict":false,"volatility":"v"},{"body_sha256":"ca586fba317867d9d67a233106e31bcde0b1201e52acedde04e63c3ea24e1d25","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"$migration_owner","parallel":"u","result":"trigger","security":false,"setof":false,"signature":"ops.guard_method_contract()","strict":false,"volatility":"v"},{"body_sha256":"cca2cf2a2d8434a7cdfe36006a5f39226cbb96be9a3f9be1c9208d3c427cfb18","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"bigint","security":true,"setof":false,"signature":"data.publish_pre_execution_analysis_batch(text,text,text,bytea,bigint)","strict":false,"volatility":"v"},{"body_sha256":"1cb5fc149a303e2da72f8c3fa5321a201228f93ebcb21e42b12e0e3ea8a7d31a","config":["search_path=pg_catalog, pg_temp"],"execute_roles":["corpus_sem_writer"],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"bigint","security":true,"setof":false,"signature":"data.publish_analysis_batch(text,text,text,bytea,bigint)","strict":false,"volatility":"v"},{"body_sha256":"618b9a41f5f94e9f70a06ef6a59f7b3c2f99f0ad1e762773686fd06b2c24caeb","config":["search_path=pg_catalog, pg_temp"],"execute_roles":["corpus_sem_reader","corpus_sem_writer"],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"void","security":true,"setof":false,"signature":"data.require_execution_release(text)","strict":false,"volatility":"v"},{"body_sha256":"225ab497a6a3c33dfa895ba3ca977de9a27f86d7777c84f92e0bc47edbba98a6","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"trigger","security":true,"setof":false,"signature":"data.guard_execution_admission()","strict":false,"volatility":"v"},{"body_sha256":"33af6322c190a8db348568ff812ad86ba22cd5bf7e5899b7b07c4a82c189d250","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"trigger","security":true,"setof":false,"signature":"data.guard_project_execution_admission()","strict":false,"volatility":"v"},{"body_sha256":"da938cc471c04444990d9022c086c214543901f93aa0d4ab5a57821dbb7f6b60","config":["search_path=pg_catalog, pg_temp"],"execute_roles":[],"language":"plpgsql","leakproof":false,"owner":"corpus_sem_publisher","parallel":"u","result":"trigger","security":true,"setof":false,"signature":"data.guard_publication_execution_admission()","strict":false,"volatility":"v"}],"inputs":[{"name":"execution/manifest.json","sha256":"a34f8dfa44bd8aaf8284b5d0c62ebc0c5735b4e95014e8139a3b86e77dfae3cc"},{"name":"execution/catalog.yaml","sha256":"76f8c19bea50bbeb85e43bcb7c2a0af5a6e78a1bf0b675a58e9cadbf97bc0231"},{"name":"execution/schema/contracts","sha256":"c7911cf9550ea31acfe0e87e3cc8e34a590b74c1c90c238ef1e87404cdb22c58"}],"model_id":"execution:48bd8dc58b721d0c0b4a19adb7fcdc518060462275922b644d304fc57b49db9d","readers":[{"relation":"sem.release","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"data.project","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"sem.artifact","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"sem.class_definition","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"sem.input","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"sem.property_definition","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"sem.registry_row","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"sem.vocabulary_member","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"data.realization","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"sem.class_hierarchy","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"sem.identity_slot","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"sem.property_applicability","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"sem.sql_admission","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"data.batch","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"data.coverage","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"data.entity","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"data.evidence","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"data.membership","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"data.typed_value","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"data.fact","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"data.membership_support","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"data.value_role","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"data.derivation","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"data.occurrence","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"data.selection","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"data.derivation_premise","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"data.occurrence_evidence","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"data.support","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"ops.method","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"ops.method_config","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"kb.document","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"kb.rendition","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"ops.run","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"kb.segment","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"ops.input_cut","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"ops.run_rendition","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"ops.task","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"kb.span","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"ops.cut_task","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"ops.intervention","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"ops.measurement","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"ops.rendition_build","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"kb.observation","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"data.assessment","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"data.evidence_source","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"data.occurrence_establishment","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"ops.task_result","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"kb.observation_input","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"data.entity_input","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"data.fact_input","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"data.occurrence_context","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"data.occurrence_evidence_role","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"data.entity_source","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"data.alternative_group","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"data.alternative_member","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"sem.conditional_rule","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"sem.conditional_atom","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"ops.completed_result","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"data.publication_intent","roles":["corpus_sem_reader","corpus_sem_writer"]},{"relation":"sem.metric_definition","roles":["corpus_sem_reader","corpus_sem_writer"]}],"triggers":[{"args":"","columns":[],"deferrable":false,"deferred":false,"function":"ops.check_source_scope()","name":"source_scope","relation":"ops.run_rendition","type":7,"when":null},{"args":"","columns":[],"deferrable":false,"deferred":false,"function":"kb.check_offsets()","name":"segment_offsets","relation":"kb.segment","type":7,"when":null},{"args":"","columns":[],"deferrable":false,"deferred":false,"function":"kb.check_offsets()","name":"span_offsets","relation":"kb.span","type":7,"when":null},{"args":"","columns":[],"deferrable":false,"deferred":false,"function":"data.check_evidence_source()","name":"evidence_source_scope","relation":"data.evidence_source","type":7,"when":null},{"args":"","columns":[],"deferrable":false,"deferred":false,"function":"kb.record_observation_inputs()","name":"observation_input_links","relation":"kb.observation","type":5,"when":null},{"args":"","columns":[],"deferrable":false,"deferred":false,"function":"ops.guard_run_lifecycle()","name":"guard_run_lifecycle","relation":"ops.run","type":19,"when":null},{"args":"","columns":[],"deferrable":false,"deferred":false,"function":"ops.guard_task_lifecycle()","name":"guard_task_lifecycle","relation":"ops.task","type":23,"when":null},{"args":"","columns":[],"deferrable":false,"deferred":false,"function":"ops.guard_cut_task()","name":"guard_cut_task","relation":"ops.cut_task","type":7,"when":null},{"args":"","columns":[],"deferrable":false,"deferred":false,"function":"data.check_entity_input()","name":"entity_input_guard","relation":"data.entity_input","type":23,"when":null},{"args":"","columns":[],"deferrable":false,"deferred":false,"function":"data.check_fact_input()","name":"fact_input_guard","relation":"data.fact_input","type":23,"when":null},{"args":"","columns":[],"deferrable":false,"deferred":false,"function":"ops.guard_source_selection()","name":"guard_source_selection","relation":"ops.task","type":23,"when":null},{"args":"","columns":[],"deferrable":false,"deferred":false,"function":"ops.guard_source_selection()","name":"guard_source_selection","relation":"ops.run_rendition","type":23,"when":null},{"args":"","columns":[],"deferrable":false,"deferred":false,"function":"ops.guard_final_cut()","name":"guard_final_cut","relation":"ops.input_cut","type":7,"when":null},{"args":"","columns":[],"deferrable":false,"deferred":false,"function":"ops.guard_task_configuration()","name":"guard_task_configuration","relation":"ops.task","type":7,"when":null},{"args":"","columns":[],"deferrable":false,"deferred":false,"function":"ops.guard_initial_task_error()","name":"guard_initial_task_error","relation":"ops.task","type":7,"when":null},{"args":"","columns":[],"deferrable":false,"deferred":false,"function":"ops.guard_execution_task()","name":"zz_execution_task","relation":"ops.task","type":23,"when":null},{"args":"","columns":[],"deferrable":false,"deferred":false,"function":"ops.guard_execution_run()","name":"zz_execution_run","relation":"ops.run","type":23,"when":null},{"args":"","columns":[],"deferrable":true,"deferred":true,"function":"ops.require_completed_result()","name":"completed_result_required","relation":"ops.run","type":17,"when":null},{"args":"","columns":[],"deferrable":false,"deferred":false,"function":"ops.guard_completed_result()","name":"immutable_completed_result","relation":"ops.completed_result","type":27,"when":null},{"args":"","columns":[],"deferrable":false,"deferred":false,"function":"data.guard_completed_output()","name":"guard_completed_output","relation":"data.realization","type":19,"when":null},{"args":"","columns":["result_realization_id"],"deferrable":true,"deferred":true,"function":"ops.require_atomic_evaluation()","name":"run_evaluation_atomic","relation":"ops.run","type":21,"when":null},{"args":"","columns":[],"deferrable":false,"deferred":false,"function":"data.validate_assessment_counterpart()","name":"validate_assessment_counterpart","relation":"data.assessment","type":23,"when":null},{"args":"","columns":[],"deferrable":false,"deferred":false,"function":"ops.validate_measurement_definition()","name":"validate_measurement_definition","relation":"ops.measurement","type":23,"when":null},{"args":"","columns":[],"deferrable":false,"deferred":false,"function":"ops.guard_measurement_custody()","name":"guard_measurement_custody","relation":"ops.measurement","type":31,"when":null},{"args":"","columns":[],"deferrable":false,"deferred":false,"function":"ops.materialize_source_measurements()","name":"materialize_source_measurements","relation":"ops.task_result","type":5,"when":null},{"args":"","columns":[],"deferrable":false,"deferred":false,"function":"ops.guard_task_method_contract()","name":"task_method_contract","relation":"ops.task","type":23,"when":null},{"args":"","columns":[],"deferrable":false,"deferred":false,"function":"ops.guard_method_contract()","name":"immutable_method_contract","relation":"ops.method","type":27,"when":null},{"args":"","columns":[],"deferrable":false,"deferred":false,"function":"data.guard_execution_admission()","name":"guard_execution_admission","relation":"data.realization","type":23,"when":null},{"args":"","columns":[],"deferrable":false,"deferred":false,"function":"data.guard_project_execution_admission()","name":"guard_project_execution_admission","relation":"data.project","type":23,"when":null},{"args":"","columns":[],"deferrable":false,"deferred":false,"function":"data.guard_publication_execution_admission()","name":"guard_publication_execution_admission","relation":"data.batch","type":7,"when":null}]}'::jsonb
$descriptor$;
ALTER FUNCTION data.execution_contract_descriptor() OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.execution_contract_descriptor() FROM PUBLIC;
CREATE FUNCTION data.require_execution_release(r text) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $admission$
DECLARE expected jsonb; spec jsonb; model jsonb; owner_name text; invalid_inference boolean;
BEGIN
 IF NOT EXISTS(SELECT FROM sem.release WHERE release_id=r) THEN RAISE EXCEPTION 'unknown execution release' USING ERRCODE='23514'; END IF;
 IF NOT EXISTS(SELECT FROM sem.release WHERE release_id=r AND profile='semantic-2') THEN RETURN; END IF;
 IF EXISTS(SELECT FROM sem.property_applicability pa WHERE pa.release_id=r AND
    (pa.constraint_scope NOT IN ('shape','accepted_value') OR pa.constraints->>'pattern' IS NOT NULL
     OR COALESCE(pa.constraints->'patterns','[]'::jsonb) NOT IN ('[]'::jsonb,'null'::jsonb))) THEN
   RAISE EXCEPTION 'unsupported required native constraint scope or pattern' USING ERRCODE='23514'; END IF;
 WITH rules AS (
  SELECT convert_from(body,'UTF8')::jsonb rule FROM sem.registry_row WHERE release_id=r AND kind='inference_rule'
 ), signatures AS (
  SELECT rule->>'kind' kind,rule->>'predicate' predicate,COALESCE(NULLIF(rule->>'target',''),rule->>'predicate') target FROM rules
 ), invalid AS (
  SELECT 1 FROM signatures s WHERE s.kind IS NULL OR s.predicate IS NULL OR s.target IS NULL OR s.kind NOT IN ('inverse','symmetric','transitive','subproperty')
   OR NOT EXISTS(SELECT FROM sem.property_applicability a WHERE a.release_id=r AND a.property_id=s.predicate)
   OR NOT EXISTS(SELECT FROM sem.property_applicability a WHERE a.release_id=r AND a.property_id=s.target)
  UNION ALL
  SELECT 1 FROM signatures s JOIN sem.property_applicability a ON a.release_id=r AND a.property_id=s.predicate
  LEFT JOIN sem.class_definition source_range ON source_range.release_id=r AND source_range.name=a.range_name
  LEFT JOIN sem.property_applicability target ON target.release_id=r AND target.property_id=s.target
   AND target.class_id=CASE WHEN s.kind='subproperty' THEN a.class_id ELSE source_range.class_id END
  LEFT JOIN sem.class_definition target_range ON target_range.release_id=r AND target_range.name=target.range_name
  WHERE COALESCE((a.constraints->>'inlined')::boolean,false) OR source_range.class_id IS NULL
   OR target.property_id IS NULL OR COALESCE((target.constraints->>'inlined')::boolean,false) OR target_range.class_id IS NULL
   OR NOT (target_range.class_id=CASE WHEN s.kind IN ('subproperty','transitive') THEN source_range.class_id ELSE a.class_id END
    OR EXISTS(SELECT FROM sem.class_hierarchy h WHERE h.release_id=r AND h.ancestor_id=target_range.class_id
      AND h.class_id=CASE WHEN s.kind IN ('subproperty','transitive') THEN source_range.class_id ELSE a.class_id END))
  UNION ALL
  SELECT 1 FROM sem.property_applicability a CROSS JOIN (VALUES('symmetric'),('transitive')) flags(name)
   WHERE a.release_id=r AND COALESCE((a.constraints->>flags.name)::boolean,false)
    AND NOT EXISTS(SELECT FROM signatures s WHERE s.kind=flags.name AND s.predicate=a.property_id AND s.target=a.property_id)
  UNION ALL
  SELECT 1 FROM sem.property_applicability a LEFT JOIN LATERAL (
    SELECT count(DISTINCT t.property_id) AS count,min(t.property_id) AS target FROM sem.property_applicability t
    WHERE t.release_id=r AND (t.property_id=a.constraints->>'inverse' OR t.constraints->>'name'=a.constraints->>'inverse')
  ) inverse_target ON true
  WHERE a.release_id=r AND NULLIF(a.constraints->>'inverse','') IS NOT NULL
   AND (inverse_target.count<>1 OR NOT EXISTS(SELECT FROM signatures s WHERE s.kind='inverse' AND s.predicate=a.property_id AND s.target=inverse_target.target))
 ) SELECT EXISTS(SELECT FROM invalid) INTO invalid_inference;
 IF invalid_inference THEN RAISE EXCEPTION 'unsupported required native binary inference profile' USING ERRCODE='23514'; END IF;
 expected:=data.execution_contract_descriptor();
 SELECT pg_get_userbyid(nspowner) INTO owner_name FROM pg_namespace WHERE nspname='sem';
 SELECT convert_from(body,'UTF8')::jsonb INTO model FROM sem.registry_row WHERE release_id=r AND kind='execution_model' AND name=expected->>'model_id';
 IF model IS NULL OR model->>'model_id' IS DISTINCT FROM expected->>'model_id' THEN RAISE EXCEPTION 'incompatible archived execution model' USING ERRCODE='23514'; END IF;
 SELECT item.value INTO spec FROM jsonb_array_elements(expected->'inputs') item
 WHERE NOT EXISTS(SELECT FROM sem.input i WHERE i.release_id=r AND i.input_kind='dependency' AND i.input_name=item.value->>'name' AND i.content_digest=item.value->>'sha256' AND encode(sha256(i.content),'hex')=item.value->>'sha256') LIMIT 1;
 IF FOUND THEN RAISE EXCEPTION 'execution input bytes differ' USING ERRCODE='23514'; END IF;
 IF (SELECT count(*) FROM sem.input WHERE release_id=r AND input_kind='dependency' AND input_name LIKE 'execution/%')<>jsonb_array_length(expected->'inputs') THEN RAISE EXCEPTION 'execution input set differs' USING ERRCODE='23514'; END IF;
 SELECT item.value INTO spec FROM jsonb_array_elements(expected->'functions') item
 LEFT JOIN pg_proc p ON p.oid=to_regprocedure(item.value->>'signature')
 LEFT JOIN pg_language l ON l.oid=p.prolang
 WHERE p.oid IS NULL OR encode(sha256(convert_to(p.prosrc,'UTF8')),'hex') IS DISTINCT FROM item.value->>'body_sha256'
 OR p.prosecdef IS DISTINCT FROM (item.value->>'security')::boolean
 OR p.proisstrict IS DISTINCT FROM (item.value->>'strict')::boolean OR p.provolatile::text IS DISTINCT FROM item.value->>'volatility' OR p.proparallel::text IS DISTINCT FROM item.value->>'parallel' OR p.proleakproof IS DISTINCT FROM (item.value->>'leakproof')::boolean
 OR l.lanname IS DISTINCT FROM item.value->>'language'
 OR p.prorettype IS DISTINCT FROM to_regtype(item.value->>'result')
 OR p.proretset IS DISTINCT FROM (item.value->>'setof')::boolean
 OR COALESCE(to_jsonb(p.proconfig),'[]'::jsonb) IS DISTINCT FROM item.value->'config'
 OR pg_get_userbyid(p.proowner) IS DISTINCT FROM (CASE WHEN item.value->>'owner'='$migration_owner' THEN owner_name ELSE item.value->>'owner' END)
 OR has_function_privilege('corpus_sem_writer',p.oid,'EXECUTE') IS DISTINCT FROM ((item.value->'execute_roles') ? 'corpus_sem_writer') OR has_function_privilege('corpus_sem_reader',p.oid,'EXECUTE') IS DISTINCT FROM ((item.value->'execute_roles') ? 'corpus_sem_reader') OR EXISTS(SELECT FROM aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) a WHERE a.grantee=0 AND a.privilege_type='EXECUTE')
 ORDER BY item.value->>'signature' LIMIT 1;
 IF FOUND THEN RAISE EXCEPTION 'native execution kernel differs: %',spec->>'signature' USING ERRCODE='23514'; END IF;
 SELECT item.value INTO spec FROM jsonb_array_elements(expected->'triggers') item
 LEFT JOIN pg_trigger t ON t.tgrelid=to_regclass(item.value->>'relation') AND t.tgname=item.value->>'name' AND NOT t.tgisinternal
 WHERE t.oid IS NULL OR t.tgenabled NOT IN ('O','A') OR t.tgfoid IS DISTINCT FROM to_regprocedure(item.value->>'function') OR t.tgtype<>(item.value->>'type')::integer OR t.tgdeferrable IS DISTINCT FROM (item.value->>'deferrable')::boolean OR t.tginitdeferred IS DISTINCT FROM (item.value->>'deferred')::boolean OR to_jsonb(ARRAY(SELECT a.attname::text FROM unnest(t.tgattr::smallint[]) WITH ORDINALITY attrs(num,position) JOIN pg_attribute a ON a.attrelid=t.tgrelid AND a.attnum=attrs.num ORDER BY attrs.position)) IS DISTINCT FROM item.value->'columns' OR pg_get_expr(t.tgqual,t.tgrelid) IS DISTINCT FROM item.value->>'when' OR encode(t.tgargs,'hex') IS DISTINCT FROM item.value->>'args' LIMIT 1;
 IF FOUND THEN RAISE EXCEPTION 'native execution guard differs: %.%',spec->>'relation',spec->>'name' USING ERRCODE='23514'; END IF;
 SELECT item.value INTO spec FROM jsonb_array_elements(expected->'readers') item
 CROSS JOIN LATERAL jsonb_array_elements_text(item.value->'roles') required_role(name)
 WHERE to_regclass(item.value->>'relation') IS NULL OR NOT has_table_privilege(required_role.name,to_regclass(item.value->>'relation'),'SELECT') LIMIT 1;
 IF FOUND THEN RAISE EXCEPTION 'required native read capability is unavailable: %',spec->>'relation' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM pg_roles WHERE rolname IN ('corpus_sem_writer','corpus_sem_reader') AND (rolsuper OR rolcreaterole OR rolbypassrls)) OR pg_has_role('corpus_sem_writer','corpus_sem_publisher','MEMBER') OR pg_has_role('corpus_sem_reader','corpus_sem_publisher','MEMBER') OR pg_has_role('corpus_sem_writer',owner_name,'MEMBER') OR pg_has_role('corpus_sem_reader',owner_name,'MEMBER') THEN RAISE EXCEPTION 'unrestricted application principal' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM (VALUES('corpus_sem_writer'),('corpus_sem_reader')) roles(name) CROSS JOIN (VALUES('sem'),('data'),('ops'),('kb')) schemas(name) WHERE has_schema_privilege(roles.name,schemas.name,'CREATE')) THEN RAISE EXCEPTION 'application schema mutation privilege' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace CROSS JOIN (VALUES('corpus_sem_writer'),('corpus_sem_reader')) roles(name) WHERE n.nspname IN ('sem','data') AND c.relkind IN ('r','p') AND (has_table_privilege(roles.name,c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER') OR has_any_column_privilege(roles.name,c.oid,'INSERT,UPDATE'))) THEN RAISE EXCEPTION 'application direct semantic write privilege' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM (VALUES('corpus_sem_writer'),('corpus_sem_reader')) roles(name) CROSS JOIN (VALUES('data.publish_contract_batch(text,text,text,bytea)'),('data.validate_state(text,text)'),('data.publish_pre_execution_analysis_batch(text,text,text,bytea,bigint)'),('data.finish_pre_contract_evaluation(bigint,text,text)')) kernels(signature) WHERE has_function_privilege(roles.name,kernels.signature,'EXECUTE')) THEN RAISE EXCEPTION 'application private kernel privilege' USING ERRCODE='23514'; END IF;
END
$admission$;
ALTER FUNCTION data.require_execution_release(text) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.require_execution_release(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.require_execution_release(text) TO corpus_sem_writer,corpus_sem_reader;
CREATE OR REPLACE FUNCTION data.guard_execution_admission() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $guard$
BEGIN IF TG_OP='UPDATE' AND (NEW.realization_id,NEW.project_id,NEW.release_id) IS DISTINCT FROM (OLD.realization_id,OLD.project_id,OLD.release_id) THEN RAISE EXCEPTION 'realization binding is immutable' USING ERRCODE='23514'; END IF; PERFORM data.require_execution_release(NEW.release_id); RETURN NEW; END
$guard$;
REVOKE ALL ON FUNCTION data.guard_execution_admission() FROM PUBLIC;
CREATE OR REPLACE FUNCTION data.guard_project_execution_admission() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $guard$
BEGIN IF TG_OP='INSERT' THEN IF NEW.generation<>0 THEN RAISE EXCEPTION 'project generation must start at zero' USING ERRCODE='23514'; END IF; ELSIF (NEW.active_release_id IS DISTINCT FROM OLD.active_release_id OR NEW.generation IS DISTINCT FROM OLD.generation) AND NEW.generation IS DISTINCT FROM OLD.generation+1 THEN RAISE EXCEPTION 'project generation must advance exactly once' USING ERRCODE='23514'; END IF; IF NEW.active_release_id IS NOT NULL THEN PERFORM data.require_execution_release(NEW.active_release_id); END IF; RETURN NEW; END
$guard$;
REVOKE ALL ON FUNCTION data.guard_project_execution_admission() FROM PUBLIC;
CREATE OR REPLACE FUNCTION data.guard_publication_execution_admission() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $guard$
BEGIN PERFORM data.require_execution_release(NEW.release_id); RETURN NEW; END
$guard$;
REVOKE ALL ON FUNCTION data.guard_publication_execution_admission() FROM PUBLIC;
DROP TRIGGER guard_execution_admission ON data.realization;
CREATE TRIGGER guard_execution_admission BEFORE INSERT OR UPDATE ON data.realization FOR EACH ROW EXECUTE FUNCTION data.guard_execution_admission();
CREATE TRIGGER guard_project_execution_admission BEFORE INSERT OR UPDATE ON data.project FOR EACH ROW EXECUTE FUNCTION data.guard_project_execution_admission();
CREATE TRIGGER guard_publication_execution_admission BEFORE INSERT ON data.batch FOR EACH ROW EXECUTE FUNCTION data.guard_publication_execution_admission();
ALTER FUNCTION data.guard_execution_admission() OWNER TO corpus_sem_publisher;
ALTER FUNCTION data.guard_project_execution_admission() OWNER TO corpus_sem_publisher;
ALTER FUNCTION data.guard_publication_execution_admission() OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION ops.check_source_scope() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.check_source_scope() TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION kb.check_offsets() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION kb.check_offsets() TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION ops.guard_task_lifecycle() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.guard_task_lifecycle() TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION ops.guard_source_selection() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.guard_source_selection() TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION ops.guard_final_cut() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.guard_final_cut() TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION ops.guard_task_configuration() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.guard_task_configuration() TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION ops.guard_initial_task_error() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.guard_initial_task_error() TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION ops.execution_edge(text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.execution_edge(text,text,text) TO corpus_sem_publisher;
GRANT EXECUTE ON FUNCTION ops.execution_edge(text,text,text) TO corpus_sem_reader;
GRANT EXECUTE ON FUNCTION ops.execution_edge(text,text,text) TO corpus_sem_writer;
REVOKE ALL ON FUNCTION ops.execution_task_state(ops.task) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.execution_task_state(ops.task) TO corpus_sem_publisher;
GRANT EXECUTE ON FUNCTION ops.execution_task_state(ops.task) TO corpus_sem_writer;
REVOKE ALL ON FUNCTION ops.guard_execution_task() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.guard_execution_task() TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION ops.guard_execution_run() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.guard_execution_run() TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION ops.require_completed_result() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.require_completed_result() TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION ops.guard_completed_result() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.guard_completed_result() TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.guard_completed_output() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.guard_completed_output() TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION ops.require_atomic_evaluation() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.require_atomic_evaluation() TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.validate_assessment_counterpart() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.validate_assessment_counterpart() TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION ops.guard_task_method_contract() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.guard_task_method_contract() TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION ops.guard_method_contract() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.guard_method_contract() TO corpus_sem_publisher;
GRANT SELECT ON sem.release TO corpus_sem_reader;
GRANT SELECT ON sem.release TO corpus_sem_writer;
GRANT SELECT ON data.project TO corpus_sem_reader;
GRANT SELECT ON data.project TO corpus_sem_writer;
GRANT SELECT ON sem.artifact TO corpus_sem_reader;
GRANT SELECT ON sem.artifact TO corpus_sem_writer;
GRANT SELECT ON sem.class_definition TO corpus_sem_reader;
GRANT SELECT ON sem.class_definition TO corpus_sem_writer;
GRANT SELECT ON sem.input TO corpus_sem_reader;
GRANT SELECT ON sem.input TO corpus_sem_writer;
GRANT SELECT ON sem.property_definition TO corpus_sem_reader;
GRANT SELECT ON sem.property_definition TO corpus_sem_writer;
GRANT SELECT ON sem.registry_row TO corpus_sem_reader;
GRANT SELECT ON sem.registry_row TO corpus_sem_writer;
GRANT SELECT ON sem.vocabulary_member TO corpus_sem_reader;
GRANT SELECT ON sem.vocabulary_member TO corpus_sem_writer;
GRANT SELECT ON data.realization TO corpus_sem_reader;
GRANT SELECT ON data.realization TO corpus_sem_writer;
GRANT SELECT ON sem.class_hierarchy TO corpus_sem_reader;
GRANT SELECT ON sem.class_hierarchy TO corpus_sem_writer;
GRANT SELECT ON sem.identity_slot TO corpus_sem_reader;
GRANT SELECT ON sem.identity_slot TO corpus_sem_writer;
GRANT SELECT ON sem.property_applicability TO corpus_sem_reader;
GRANT SELECT ON sem.property_applicability TO corpus_sem_writer;
GRANT SELECT ON sem.sql_admission TO corpus_sem_reader;
GRANT SELECT ON sem.sql_admission TO corpus_sem_writer;
GRANT SELECT ON data.batch TO corpus_sem_reader;
GRANT SELECT ON data.batch TO corpus_sem_writer;
GRANT SELECT ON data.coverage TO corpus_sem_reader;
GRANT SELECT ON data.coverage TO corpus_sem_writer;
GRANT SELECT ON data.entity TO corpus_sem_reader;
GRANT SELECT ON data.entity TO corpus_sem_writer;
GRANT SELECT ON data.evidence TO corpus_sem_reader;
GRANT SELECT ON data.evidence TO corpus_sem_writer;
GRANT SELECT ON data.membership TO corpus_sem_reader;
GRANT SELECT ON data.membership TO corpus_sem_writer;
GRANT SELECT ON data.typed_value TO corpus_sem_reader;
GRANT SELECT ON data.typed_value TO corpus_sem_writer;
GRANT SELECT ON data.fact TO corpus_sem_reader;
GRANT SELECT ON data.fact TO corpus_sem_writer;
GRANT SELECT ON data.membership_support TO corpus_sem_reader;
GRANT SELECT ON data.membership_support TO corpus_sem_writer;
GRANT SELECT ON data.value_role TO corpus_sem_reader;
GRANT SELECT ON data.value_role TO corpus_sem_writer;
GRANT SELECT ON data.derivation TO corpus_sem_reader;
GRANT SELECT ON data.derivation TO corpus_sem_writer;
GRANT SELECT ON data.occurrence TO corpus_sem_reader;
GRANT SELECT ON data.occurrence TO corpus_sem_writer;
GRANT SELECT ON data.selection TO corpus_sem_reader;
GRANT SELECT ON data.selection TO corpus_sem_writer;
GRANT SELECT ON data.derivation_premise TO corpus_sem_reader;
GRANT SELECT ON data.derivation_premise TO corpus_sem_writer;
GRANT SELECT ON data.occurrence_evidence TO corpus_sem_reader;
GRANT SELECT ON data.occurrence_evidence TO corpus_sem_writer;
GRANT SELECT ON data.support TO corpus_sem_reader;
GRANT SELECT ON data.support TO corpus_sem_writer;
GRANT SELECT ON ops.method TO corpus_sem_reader;
GRANT SELECT ON ops.method TO corpus_sem_writer;
GRANT SELECT ON ops.method_config TO corpus_sem_reader;
GRANT SELECT ON ops.method_config TO corpus_sem_writer;
GRANT SELECT ON kb.document TO corpus_sem_reader;
GRANT SELECT ON kb.document TO corpus_sem_writer;
GRANT SELECT ON kb.rendition TO corpus_sem_reader;
GRANT SELECT ON kb.rendition TO corpus_sem_writer;
GRANT SELECT ON ops.run TO corpus_sem_reader;
GRANT SELECT ON ops.run TO corpus_sem_writer;
GRANT SELECT ON kb.segment TO corpus_sem_reader;
GRANT SELECT ON kb.segment TO corpus_sem_writer;
GRANT SELECT ON ops.input_cut TO corpus_sem_reader;
GRANT SELECT ON ops.input_cut TO corpus_sem_writer;
GRANT SELECT ON ops.run_rendition TO corpus_sem_reader;
GRANT SELECT ON ops.run_rendition TO corpus_sem_writer;
GRANT SELECT ON ops.task TO corpus_sem_reader;
GRANT SELECT ON ops.task TO corpus_sem_writer;
GRANT SELECT ON kb.span TO corpus_sem_reader;
GRANT SELECT ON kb.span TO corpus_sem_writer;
GRANT SELECT ON ops.cut_task TO corpus_sem_reader;
GRANT SELECT ON ops.cut_task TO corpus_sem_writer;
GRANT SELECT ON ops.intervention TO corpus_sem_reader;
GRANT SELECT ON ops.intervention TO corpus_sem_writer;
GRANT SELECT ON ops.measurement TO corpus_sem_reader;
GRANT SELECT ON ops.measurement TO corpus_sem_writer;
GRANT SELECT ON ops.rendition_build TO corpus_sem_reader;
GRANT SELECT ON ops.rendition_build TO corpus_sem_writer;
GRANT SELECT ON kb.observation TO corpus_sem_reader;
GRANT SELECT ON kb.observation TO corpus_sem_writer;
GRANT SELECT ON data.assessment TO corpus_sem_reader;
GRANT SELECT ON data.assessment TO corpus_sem_writer;
GRANT SELECT ON data.evidence_source TO corpus_sem_reader;
GRANT SELECT ON data.evidence_source TO corpus_sem_writer;
GRANT SELECT ON data.occurrence_establishment TO corpus_sem_reader;
GRANT SELECT ON data.occurrence_establishment TO corpus_sem_writer;
GRANT SELECT ON ops.task_result TO corpus_sem_reader;
GRANT SELECT ON ops.task_result TO corpus_sem_writer;
GRANT SELECT ON kb.observation_input TO corpus_sem_reader;
GRANT SELECT ON kb.observation_input TO corpus_sem_writer;
GRANT SELECT ON sem.conditional_rule TO corpus_sem_reader;
GRANT SELECT ON sem.conditional_rule TO corpus_sem_writer;
GRANT SELECT ON sem.conditional_atom TO corpus_sem_reader;
GRANT SELECT ON sem.conditional_atom TO corpus_sem_writer;
GRANT SELECT ON ops.completed_result TO corpus_sem_reader;
GRANT SELECT ON ops.completed_result TO corpus_sem_writer;
GRANT SELECT ON data.publication_intent TO corpus_sem_reader;
GRANT SELECT ON data.publication_intent TO corpus_sem_writer;
GRANT SELECT ON sem.metric_definition TO corpus_sem_reader;
GRANT SELECT ON sem.metric_definition TO corpus_sem_writer;
SET LOCAL ROLE corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.canonical_json(jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.canonical_json(jsonb) TO corpus_sem_reader;
GRANT EXECUTE ON FUNCTION data.canonical_json(jsonb) TO corpus_sem_writer;
REVOKE ALL ON FUNCTION data.decimal_canonical(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.decimal_canonical(text) TO corpus_sem_reader;
GRANT EXECUTE ON FUNCTION data.decimal_canonical(text) TO corpus_sem_writer;
REVOKE ALL ON FUNCTION data.compare_decimal(text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION data.value_meaning(text,text,text,text[],boolean) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.value_meaning(text,text,text,text[],boolean) TO corpus_sem_reader;
GRANT EXECUTE ON FUNCTION data.value_meaning(text,text,text,text[],boolean) TO corpus_sem_writer;
REVOKE ALL ON FUNCTION data.value_matches(text,text,text,text,boolean) FROM PUBLIC;
REVOKE ALL ON FUNCTION data.fact_identity(text,text,text,text,text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION ops.capture_cut(bigint,text,boolean) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.capture_cut(bigint,text,boolean) TO corpus_sem_writer;
REVOKE ALL ON FUNCTION ops.create_run(text,text,text,bigint,bytea,text,bigint,jsonb,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.create_run(text,text,text,bigint,bytea,text,bigint,jsonb,text,text) TO corpus_sem_writer;
REVOKE ALL ON FUNCTION data.check_evidence_source() FROM PUBLIC;
REVOKE ALL ON FUNCTION data.inference_seeds(text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.inference_seeds(text,text) TO corpus_sem_reader;
GRANT EXECUTE ON FUNCTION data.inference_seeds(text,text) TO corpus_sem_writer;
REVOKE ALL ON FUNCTION data.validate_pre_inference_state(text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION data.begin_evaluation(bigint,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.begin_evaluation(bigint,text) TO corpus_sem_writer;
REVOKE ALL ON FUNCTION data.initialize_source_project(text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.initialize_source_project(text,text,text) TO corpus_sem_writer;
REVOKE ALL ON FUNCTION kb.record_observation_inputs() FROM PUBLIC;
REVOKE ALL ON FUNCTION ops.guard_run_lifecycle() FROM PUBLIC;
REVOKE ALL ON FUNCTION ops.valid_reuse(ops.task) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.valid_reuse(ops.task) TO corpus_sem_writer;
REVOKE ALL ON FUNCTION ops.guard_cut_task() FROM PUBLIC;
REVOKE ALL ON FUNCTION ops.end_source_run(bigint,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.end_source_run(bigint,jsonb) TO corpus_sem_writer;
REVOKE ALL ON FUNCTION data.report_field(jsonb,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION data.check_entity_input() FROM PUBLIC;
REVOKE ALL ON FUNCTION data.begin_pre_input_stage() FROM PUBLIC;
REVOKE ALL ON FUNCTION data.begin_stage() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.begin_stage() TO corpus_sem_writer;
REVOKE ALL ON FUNCTION data.end_pre_input_stage() FROM PUBLIC;
REVOKE ALL ON FUNCTION data.end_stage() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.end_stage() TO corpus_sem_writer;
REVOKE ALL ON FUNCTION data.check_fact_input() FROM PUBLIC;
REVOKE ALL ON FUNCTION data.validate_occurrence_context(text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION data.validate_entity_source(text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION data.finish_pre_context_evaluation(bigint,text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION ops.lock_input_snapshot(bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.lock_input_snapshot(bigint) TO corpus_sem_writer;
REVOKE ALL ON FUNCTION data.validate_property_pre_fact_references(text,text,text,text,jsonb) FROM PUBLIC;
REVOKE ALL ON FUNCTION data.validate_property(text,text,text,text,jsonb) FROM PUBLIC;
REVOKE ALL ON FUNCTION data.finish_pre_source_identity_evaluation(bigint,text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION ops.hold_agent_result(bigint,bigint,text,text,boolean,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.hold_agent_result(bigint,bigint,text,text,boolean,jsonb) TO corpus_sem_writer;
REVOKE ALL ON FUNCTION data.validate_alternatives(text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION data.validate_conditions(text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION data.validate_pre_contract_state(text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION data.validate_state(text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION data.finish_pre_contract_evaluation(bigint,text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION data.finish_evaluation(bigint,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.finish_evaluation(bigint,text,text) TO corpus_sem_writer;
REVOKE ALL ON FUNCTION data.publish_contract_batch(text,text,text,bytea) FROM PUBLIC;
REVOKE ALL ON FUNCTION data.publish_batch(text,text,text,bytea) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.publish_batch(text,text,text,bytea) TO corpus_sem_writer;
REVOKE ALL ON FUNCTION data.publish_derived_batch(text,text,text,bytea,text,text,bigint,text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.publish_derived_batch(text,text,text,bytea,text,text,bigint,text,text,text) TO corpus_sem_writer;
REVOKE ALL ON FUNCTION ops.renew_claim(bigint,bigint,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.renew_claim(bigint,bigint,text) TO corpus_sem_writer;
REVOKE ALL ON FUNCTION ops.release_claim(bigint,bigint,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.release_claim(bigint,bigint,text,text) TO corpus_sem_writer;
REVOKE ALL ON FUNCTION ops.complete_task(bigint,bigint,text,jsonb,text,jsonb,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.complete_task(bigint,bigint,text,jsonb,text,jsonb,jsonb) TO corpus_sem_writer;
REVOKE ALL ON FUNCTION ops.validate_measurement_definition() FROM PUBLIC;
REVOKE ALL ON FUNCTION ops.decode_source_value(jsonb) FROM PUBLIC;
REVOKE ALL ON FUNCTION ops.guard_measurement_custody() FROM PUBLIC;
REVOKE ALL ON FUNCTION ops.materialize_source_measurements() FROM PUBLIC;
REVOKE ALL ON FUNCTION data.publish_pre_execution_analysis_batch(text,text,text,bytea,bigint) FROM PUBLIC;
REVOKE ALL ON FUNCTION data.publish_analysis_batch(text,text,text,bytea,bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.publish_analysis_batch(text,text,text,bytea,bigint) TO corpus_sem_writer;
REVOKE ALL ON FUNCTION data.require_execution_release(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.require_execution_release(text) TO corpus_sem_reader;
GRANT EXECUTE ON FUNCTION data.require_execution_release(text) TO corpus_sem_writer;
REVOKE ALL ON FUNCTION data.guard_execution_admission() FROM PUBLIC;
REVOKE ALL ON FUNCTION data.guard_project_execution_admission() FROM PUBLIC;
REVOKE ALL ON FUNCTION data.guard_publication_execution_admission() FROM PUBLIC;
GRANT SELECT ON data.entity_input TO corpus_sem_reader;
GRANT SELECT ON data.entity_input TO corpus_sem_writer;
GRANT SELECT ON data.fact_input TO corpus_sem_reader;
GRANT SELECT ON data.fact_input TO corpus_sem_writer;
GRANT SELECT ON data.occurrence_context TO corpus_sem_reader;
GRANT SELECT ON data.occurrence_context TO corpus_sem_writer;
GRANT SELECT ON data.occurrence_evidence_role TO corpus_sem_reader;
GRANT SELECT ON data.occurrence_evidence_role TO corpus_sem_writer;
GRANT SELECT ON data.entity_source TO corpus_sem_reader;
GRANT SELECT ON data.entity_source TO corpus_sem_writer;
GRANT SELECT ON data.alternative_group TO corpus_sem_reader;
GRANT SELECT ON data.alternative_group TO corpus_sem_writer;
GRANT SELECT ON data.alternative_member TO corpus_sem_reader;
GRANT SELECT ON data.alternative_member TO corpus_sem_writer;
GRANT EXECUTE ON FUNCTION data.require_execution_release(text) TO __MIGRATION_OWNER__;
REVOKE ALL ON FUNCTION data.execution_contract_descriptor() FROM PUBLIC;
REVOKE ALL ON FUNCTION data.publish_pre_execution_analysis_batch(text,text,text,bytea,bigint) FROM corpus_sem_writer,corpus_sem_reader;
SET LOCAL ROLE __MIGRATION_OWNER__;
