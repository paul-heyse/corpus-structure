-- One bounded immutable neighborhood per already authenticated inventory/profile.
CREATE OR REPLACE FUNCTION ops.contextual_mutual_neighbors(inv jsonb,profile jsonb,vectors jsonb)
RETURNS jsonb LANGUAGE sql STABLE SET search_path=pg_catalog,pg_temp AS $$
 WITH targets AS MATERIALIZED (
  SELECT t->>'target_id' AS id,t->>'representation_digest' AS digest,t->>'source_binding' AS source
  FROM jsonb_array_elements(inv->'targets') t
 ), eligible AS MATERIALIZED (
  SELECT t.id,t.digest,(v->'values')::text::public.vector AS vector
  FROM targets t JOIN jsonb_array_elements(vectors) v ON v->>'object_id'=t.id
  WHERE v->>'profile_id'=profile->>'profile_id' AND v->>'representation_digest'=t.digest
   AND v->>'source_binding'=t.source
   AND public.vector_dims((v->'values')::text::public.vector)=(profile->>'dimension')::integer
   AND abs(public.vector_norm((v->'values')::text::public.vector)-1)<=0.00001
 ), coverage AS (
  SELECT CASE WHEN NOT EXISTS(SELECT FROM targets) THEN 'completed'
   WHEN profile IS NULL THEN 'profile_unavailable'
   WHEN (SELECT count(*) FROM targets)<>(SELECT count(*) FROM eligible)
     OR (SELECT count(*) FROM eligible)<>(SELECT count(DISTINCT id) FROM eligible)
     OR (SELECT count(*) FROM targets t JOIN jsonb_array_elements(vectors) v
         ON v->>'object_id'=t.id AND v->>'profile_id'=profile->>'profile_id')
        <>(SELECT count(*) FROM eligible)
   THEN 'vector_coverage_unavailable' ELSE 'completed' END AS status
 ), representatives AS MATERIALIZED (
  SELECT e.*,g->>'target_id' AS group_id
  FROM coverage c,jsonb_array_elements(inv->'semantic_groups') g
  JOIN eligible e ON e.id=g->'member_target_ids'->>0
  WHERE c.status='completed'
 ), directed AS MATERIALIZED (
  SELECT a.id AS from_id,b.id AS to_id,
   row_number() OVER(PARTITION BY a.id ORDER BY b.distance,b.id COLLATE "C") AS rank_,b.distance
  FROM representatives a CROSS JOIN LATERAL (
   SELECT b.id,a.vector OPERATOR(public.<=>) b.vector AS distance
   FROM representatives b WHERE b.id<>a.id ORDER BY distance,b.id COLLATE "C" LIMIT 5
  ) b
 ), mutual AS (
  SELECT d.from_id,d.to_id,d.rank_ AS left_rank,r.rank_ AS right_rank,d.distance
  FROM directed d JOIN directed r ON r.from_id=d.to_id AND r.to_id=d.from_id
  WHERE d.from_id COLLATE "C"<d.to_id COLLATE "C"
 )
 SELECT jsonb_strip_nulls(jsonb_build_object(
  'policy','mutual-exact-cosine-top5-2','inventory_id',inv->>'inventory_id',
  'profile_id',profile->>'profile_id','status',c.status,
  'directed_ranks',COALESCE((
   SELECT jsonb_agg(jsonb_build_object('from_id',from_id,'to_id',to_id,'rank',rank_,'distance',distance)
    ORDER BY from_id COLLATE "C",rank_) FROM directed
  ),'[]'::jsonb),
  'edges',COALESCE((
   SELECT jsonb_agg(jsonb_build_object('left_id',m.from_id,'right_id',m.to_id,
    'left_group',a.group_id,'right_group',b.group_id,
    'left_digest',a.digest,'right_digest',b.digest,
    'left_rank',m.left_rank,'right_rank',m.right_rank,'distance',m.distance)
    ORDER BY m.from_id COLLATE "C",m.to_id COLLATE "C")
   FROM mutual m JOIN representatives a ON a.id=m.from_id JOIN representatives b ON b.id=m.to_id
  ),'[]'::jsonb)))
 FROM coverage c
$$;
