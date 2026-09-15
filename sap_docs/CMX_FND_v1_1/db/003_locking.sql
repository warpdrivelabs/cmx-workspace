-- Proposed runtime guards. NOT executed in a PostgreSQL instance here.
-- Apply after 001. All functions are SECURITY INVOKER; IAM/SoD remain mandatory.
BEGIN;
CREATE FUNCTION cmx_fnd.prevent_revision_rewrite() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,cmx_fnd AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'FND_REVISION_DELETE_FORBIDDEN'; END IF;
 IF (to_jsonb(NEW)-'recorded_to') IS DISTINCT FROM (to_jsonb(OLD)-'recorded_to')
    OR OLD.recorded_to IS NOT NULL OR NEW.recorded_to IS NULL THEN
   RAISE EXCEPTION 'FND_REVISION_REWRITE_FORBIDDEN';
 END IF;
 RETURN NEW;
END $$;
DO $$ DECLARE r record; BEGIN
 FOR r IN SELECT table_name FROM information_schema.columns
 WHERE table_schema='cmx_fnd' AND column_name='recorded_to' LOOP
  EXECUTE format('CREATE TRIGGER revision_close_only BEFORE UPDATE OR DELETE ON cmx_fnd.%I FOR EACH ROW EXECUTE FUNCTION cmx_fnd.prevent_revision_rewrite()',r.table_name);
 END LOOP;
END $$;
CREATE FUNCTION cmx_fnd.bump_gate_version() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,cmx_fnd AS $$
BEGIN
 IF (NEW.tenant_id,NEW.mandt,NEW.bukrs,NEW.rldnr,NEW.gjahr,NEW.poper,NEW.application)
  IS DISTINCT FROM (OLD.tenant_id,OLD.mandt,OLD.bukrs,OLD.rldnr,OLD.gjahr,OLD.poper,OLD.application)
 THEN RAISE EXCEPTION 'FND_PERIOD_GATE_KEY_IMMUTABLE'; END IF;
 IF OLD.status='HARD_CLOSED' AND NEW.status<>OLD.status THEN
  RAISE EXCEPTION 'FND_HARD_CLOSE_REQUIRES_SPECIAL_MIGRATION'; END IF;
 IF NEW.status IS DISTINCT FROM OLD.status AND NEW.approved_change_id IS NULL THEN
  RAISE EXCEPTION 'FND_GATE_APPROVAL_REFERENCE_REQUIRED'; END IF;
 NEW.version:=OLD.version+1;
 RETURN NEW;
END $$;
CREATE TRIGGER gate_version BEFORE UPDATE ON cmx_fnd.period_gate
 FOR EACH ROW EXECUTE FUNCTION cmx_fnd.bump_gate_version();

CREATE FUNCTION cmx_fnd.lock_inventory_context(
 p_bukrs varchar, p_posting_date date, p_expected_release uuid,
 p_expected_versions jsonb
) RETURNS TABLE(gate_key text, gate_version bigint)
LANGUAGE plpgsql SET search_path=pg_catalog,cmx_fnd AS $$
DECLARE
 t uuid; c text; actual_release uuid; b record; fp record; g record;
 app_name text; k text; n integer:=0; count_expected integer;
BEGIN
 t:=nullif(current_setting('app.tenant_id',true),'')::uuid;
 c:=nullif(current_setting('app.mandt',true),'');
 IF t IS NULL OR c IS NULL THEN RAISE EXCEPTION 'FND_SCOPE_REQUIRED'; END IF;
 IF p_posting_date IS NULL OR p_expected_release IS NULL OR p_expected_versions IS NULL
    OR jsonb_typeof(p_expected_versions)<>'object' THEN
  RAISE EXCEPTION 'FND_LOCK_INPUT_INVALID'; END IF;
 -- Shared head lock blocks publication while this inventory operation is committing.
 SELECT h.active_release_id INTO actual_release FROM cmx_fnd.config_head h
  WHERE h.tenant_id=t AND h.mandt=c FOR SHARE;
 IF actual_release IS NULL OR actual_release<>p_expected_release THEN
  RAISE EXCEPTION 'FND_RELEASE_STALE'; END IF;
 IF NOT EXISTS(SELECT 1 FROM cmx_fnd.foundation_release r WHERE r.tenant_id=t
   AND r.mandt=c AND r.release_id=actual_release AND r.status='PUBLISHED') THEN
  RAISE EXCEPTION 'FND_RELEASE_NOT_PUBLISHED'; END IF;
 -- Caller cannot omit a required ledger: derive the set from published configuration.
 FOR b IN SELECT * FROM cmx_fnd.book_config bc WHERE bc.tenant_id=t AND bc.mandt=c
  AND bc.release_id=actual_release AND bc.bukrs=p_bukrs AND bc.required_for_inventory
  AND bc.active_from<=p_posting_date AND (bc.active_to IS NULL OR p_posting_date<bc.active_to)
  ORDER BY bc.rldnr LOOP
  IF b.inventory_capability<>'ENABLED_AND_VALIDATED' THEN
   RAISE EXCEPTION 'FND_LEDGER_INTEGRATION_INCOMPLETE'; END IF;
  SELECT f.gjahr,f.poper INTO fp FROM cmx_fnd.fiscal_period_config f
   WHERE f.tenant_id=t AND f.mandt=c AND f.release_id=actual_release
   AND f.periv=b.periv AND f.date_from<=p_posting_date AND p_posting_date<f.date_to;
  IF NOT FOUND THEN RAISE EXCEPTION 'FND_CALENDAR_GAP'; END IF;
  -- Deliberately restricted to ordinary inventory operations. No special periods,
  -- no permitted-closing-job bypass, no predictive/technical ledger emulation.
  FOREACH app_name IN ARRAY ARRAY['FI','MM'] LOOP
   k:=p_bukrs||'/'||b.rldnr||'/'||fp.gjahr||'/'||fp.poper||'/'||app_name;
   IF NOT p_expected_versions ? k THEN RAISE EXCEPTION 'FND_GATE_VERSION_MISSING: %',k; END IF;
   SELECT pg.status,pg.version INTO g FROM cmx_fnd.period_gate pg
    WHERE pg.tenant_id=t AND pg.mandt=c AND pg.bukrs=p_bukrs AND pg.rldnr=b.rldnr
      AND pg.gjahr=fp.gjahr AND pg.poper=fp.poper AND pg.application=app_name FOR SHARE;
   IF NOT FOUND OR g.status<>'OPEN' OR g.version<>(p_expected_versions->>k)::bigint THEN
    RAISE EXCEPTION 'FND_PERIOD_GATE_CLOSED_OR_STALE: %',k; END IF;
   gate_key:=k; gate_version:=g.version; RETURN NEXT; n:=n+1;
  END LOOP;
 END LOOP;
 IF n=0 THEN RAISE EXCEPTION 'FND_REQUIRED_LEDGER_MISSING'; END IF;
 SELECT count(*) INTO count_expected FROM jsonb_object_keys(p_expected_versions);
 IF n<>count_expected THEN RAISE EXCEPTION 'FND_EXTRA_OR_UNEXPECTED_GATE'; END IF;
END $$;
COMMIT;
-- Must run inside THE SAME explicit transaction as the eventual stock/accounting write.
-- An autocommitted function call followed by a separate posting has no lock guarantee.
