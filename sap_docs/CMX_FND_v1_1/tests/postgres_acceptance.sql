-- NOT RUN in the current environment.
-- Run after migrations and the explicit demo seed in an isolated test database.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL app.tenant_id='11111111-1111-1111-1111-111111111111';
SET LOCAL app.mandt='100';
DO $$ DECLARE v text; n integer; caught boolean:=false; BEGIN
 SELECT k.bwkey||'/'||k.bukrs INTO v
 FROM cmx_fnd.plant_config w JOIN cmx_fnd.valuation_area_config k
 USING(tenant_id,mandt,release_id,bwkey)
 WHERE w.tenant_id='11111111-1111-1111-1111-111111111111'
 AND w.mandt='100' AND w.release_id='22222222-2222-2222-2222-222222222222' AND w.werks='1100';
 IF v IS DISTINCT FROM 'V100/1000' THEN RAISE EXCEPTION 'TEST_ORG_CHAIN_FAILED'; END IF;
 SELECT gjahr::text||'/'||poper::text INTO v FROM cmx_fnd.fiscal_period_config
 WHERE tenant_id='11111111-1111-1111-1111-111111111111' AND mandt='100'
  AND release_id='22222222-2222-2222-2222-222222222222' AND periv='A4'
  AND date_from<='2027-01-15' AND '2027-01-15'<date_to;
 IF v IS DISTINCT FROM '2026/10' THEN RAISE EXCEPTION 'TEST_CALENDAR_FAILED'; END IF;
 BEGIN
  UPDATE cmx_fnd.plant_config SET name='ILLEGAL_CHANGE'
   WHERE tenant_id='11111111-1111-1111-1111-111111111111' AND mandt='100'
   AND release_id='22222222-2222-2222-2222-222222222222' AND werks='1100';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM<>'FND_RELEASE_IMMUTABLE_OR_MISSING' THEN RAISE; END IF;
  caught:=true;
 END;
 IF NOT caught THEN RAISE EXCEPTION 'TEST_PUBLISHED_IMMUTABILITY_FAILED'; END IF;
 SELECT count(*) INTO n FROM cmx_fnd.lock_inventory_context(
 '1000','2026-09-14','22222222-2222-2222-2222-222222222222',
 '{"1000/0L/2026/9/FI":1,"1000/0L/2026/9/MM":1,"1000/2L/2026/6/FI":1,"1000/2L/2026/6/MM":1}'::jsonb);
 IF n<>4 THEN RAISE EXCEPTION 'TEST_LEDGER_GATES_FAILED'; END IF;
END $$;
ROLLBACK;
-- RLS MUST ALSO be tested using a normal non-owner/non-BYPASSRLS role.
-- A passing SELECT executed as a superuser is not an RLS test.
