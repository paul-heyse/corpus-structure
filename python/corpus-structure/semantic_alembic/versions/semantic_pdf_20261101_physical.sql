-- The imported semantic declarations changed identity, with identical physical CHECKs.
-- Zero ordinary DDL was emitted by the reviewed Alembic metadata comparison.
INSERT INTO sem.physical_contract(physical_id,checks,source_digest)
SELECT 'physical:e5b55f9dada229cc1df9828ae0269cd24ff109ef3c0121ff0f7be5d174dc434c',checks,'86383f3b5ef343260f16964b435dcda302a500a18aa367037ec82fbdc8bbade0' FROM sem.physical_contract
WHERE physical_id='physical:d29b0f9ea98c65469396cd96d0eeb2e74a8e9f21ca1451b72f131af6d26e3bc5' AND source_digest='86383f3b5ef343260f16964b435dcda302a500a18aa367037ec82fbdc8bbade0'
ON CONFLICT DO NOTHING;
DO $receipt$ BEGIN
 IF NOT EXISTS(SELECT FROM sem.physical_contract current_
 JOIN sem.physical_contract previous_ ON current_.checks=previous_.checks
 WHERE current_.physical_id='physical:e5b55f9dada229cc1df9828ae0269cd24ff109ef3c0121ff0f7be5d174dc434c' AND previous_.physical_id='physical:d29b0f9ea98c65469396cd96d0eeb2e74a8e9f21ca1451b72f131af6d26e3bc5'
 AND current_.source_digest='86383f3b5ef343260f16964b435dcda302a500a18aa367037ec82fbdc8bbade0' AND previous_.source_digest=current_.source_digest) THEN
 RAISE EXCEPTION 'structured PDF physical contract receipt differs' USING ERRCODE='23514';
 END IF;
END $receipt$;
