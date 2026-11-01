-- The imported semantic declarations changed identity, with identical physical CHECKs.
-- Zero ordinary DDL was emitted by the reviewed Alembic metadata comparison.
INSERT INTO sem.physical_contract(physical_id,checks,source_digest)
SELECT 'physical:a421ce2f95e22be09db50bd3ac68d374d9a56c22cc9963da4f798d7a02611e4e',checks,'86383f3b5ef343260f16964b435dcda302a500a18aa367037ec82fbdc8bbade0' FROM sem.physical_contract
WHERE physical_id='physical:86b7be5b6fa5da4fcfac83471753b186543ce8029a75ce91f456fd965c35d4cd' AND source_digest='86383f3b5ef343260f16964b435dcda302a500a18aa367037ec82fbdc8bbade0'
ON CONFLICT DO NOTHING;
DO $receipt$ BEGIN
 IF NOT EXISTS(SELECT FROM sem.physical_contract current_
 JOIN sem.physical_contract previous_ ON current_.checks=previous_.checks
 WHERE current_.physical_id='physical:a421ce2f95e22be09db50bd3ac68d374d9a56c22cc9963da4f798d7a02611e4e' AND previous_.physical_id='physical:86b7be5b6fa5da4fcfac83471753b186543ce8029a75ce91f456fd965c35d4cd'
 AND current_.source_digest='86383f3b5ef343260f16964b435dcda302a500a18aa367037ec82fbdc8bbade0' AND previous_.source_digest=current_.source_digest) THEN
 RAISE EXCEPTION 'PDF projection policy physical contract receipt differs' USING ERRCODE='23514';
 END IF;
END $receipt$;
