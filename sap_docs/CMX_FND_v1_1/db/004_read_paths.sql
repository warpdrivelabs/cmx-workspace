-- Prepared queries use only caller-bound values. Not PostgreSQL-runtime-tested here.
-- Always establish trusted tenant/client with SET LOCAL in the surrounding transaction.
PREPARE fnd_resolve_plant(uuid,varchar,uuid,varchar,varchar,varchar) AS
 SELECT w.werks,k.bwkey,k.bukrs,c.ktopl,c.currency,c.periv,c.opvar,
        l.lgort,e.ekorg,e.bukrs AS purchasing_company
 FROM cmx_fnd.plant_config w
 JOIN cmx_fnd.valuation_area_config k USING(tenant_id,mandt,release_id,bwkey)
 JOIN cmx_fnd.company_config c USING(tenant_id,mandt,release_id,bukrs)
 JOIN cmx_fnd.storage_location_config l USING(tenant_id,mandt,release_id,werks)
 JOIN cmx_fnd.purchasing_plant_config pw USING(tenant_id,mandt,release_id,werks)
 JOIN cmx_fnd.purchasing_org_config e USING(tenant_id,mandt,release_id,ekorg)
 WHERE w.tenant_id=$1 AND w.mandt=$2 AND w.release_id=$3
   AND w.werks=$4 AND l.lgort=$5 AND e.ekorg=$6
   AND (e.bukrs IS NULL OR e.bukrs=k.bukrs);
-- Zero rows means missing / invalid scope, NOT an automatic fallback.

PREPARE fnd_resolve_material_price(uuid,varchar,varchar,varchar,varchar,varchar,varchar,date,timestamptz) AS
 SELECT revision_id,kalnr,rldnr,external_currency_type,price_type,price_subtype,
        currency,valuation_unit,numerator,denominator,valid_from,valid_to
 FROM cmx_fnd.material_price_version
 WHERE tenant_id=$1 AND mandt=$2 AND kalnr=$3 AND rldnr=$4
  AND external_currency_type=$5 AND price_type=$6 AND price_subtype=$7
  AND valid_from<=$8 AND (valid_to IS NULL OR $8<valid_to)
  AND recorded_from<=$9 AND (recorded_to IS NULL OR $9<recorded_to);
-- No LIMIT 1: 0=missing; >1=corrupt/ambiguous; exactly 1=resolved.
-- Currency and unit must also match the book and material snapshot.
