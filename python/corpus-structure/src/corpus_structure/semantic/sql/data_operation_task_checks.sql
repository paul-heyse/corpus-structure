  IF current_user<>'corpus_sem_publisher' OR NOT EXISTS(SELECT FROM ops.data_request r
    WHERE r.id=NEW.data_request_id AND r.release_id=NEW.release_id AND r.generation=NEW.data_generation) THEN
   RAISE EXCEPTION 'data task requires protected admitted request generation' USING ERRCODE='23514'; END IF;
  IF TG_OP='INSERT' THEN
   IF NEW.status<>__DDO_TASK_INITIAL__ OR NEW.attempt<>0 OR NEW.claimed_by IS NOT NULL OR NEW.lease_until IS NOT NULL THEN RAISE EXCEPTION 'invalid initial data task'; END IF;
  ELSE
   IF (NEW.data_request_id,NEW.data_generation,NEW.release_id,NEW.invocation_key) IS DISTINCT FROM
      (OLD.data_request_id,OLD.data_generation,OLD.release_id,OLD.invocation_key) OR OLD.status IN (__DDO_TASK_TERMINAL__) THEN RAISE EXCEPTION 'data task association/terminal state immutable'; END IF;
   IF NEW.attempt<>OLD.attempt THEN
    IF NEW.attempt<>OLD.attempt+1 OR NEW.status<>__DDO_TASK_RUNNING__ OR nullif(NEW.claimed_by,'') IS NULL OR NEW.lease_until IS NULL OR NEW.lease_until<=clock_timestamp()
    OR NOT (__DDO_TASK_NEW_ATTEMPT__) OR (OLD.status=__DDO_TASK_RUNNING__ AND (OLD.lease_until IS NULL OR OLD.lease_until>clock_timestamp())) THEN RAISE EXCEPTION 'invalid data claim fence'; END IF;
   ELSIF NEW.claimed_by IS DISTINCT FROM OLD.claimed_by THEN RAISE EXCEPTION 'data holder requires new attempt';
   ELSIF NEW.status<>OLD.status AND NOT (__DDO_TASK_SAME_ATTEMPT__) THEN RAISE EXCEPTION 'invalid data task transition'; END IF;
  END IF;
  IF NEW.status=__DDO_TASK_RUNNING__ AND (NEW.attempt<=0 OR NEW.claimed_by IS NULL OR NEW.lease_until IS NULL) THEN RAISE EXCEPTION 'data running task requires exact fence'; END IF;
  IF NEW.status<>__DDO_TASK_RUNNING__ AND NEW.lease_until IS NOT NULL THEN RAISE EXCEPTION 'data terminal task retains lease'; END IF;
  IF NEW.status IN (__DDO_TASK_RECEIPT_REQUIRED__) AND NEW.result_digest IS NULL THEN RAISE EXCEPTION 'data completion requires receipt'; END IF;
  RETURN NEW;
