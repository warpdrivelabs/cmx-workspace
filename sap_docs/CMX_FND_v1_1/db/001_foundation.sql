-- CMX FND v1.1 proposed PostgreSQL migration. NOT applied in this environment.
-- PostgreSQL 15+ design target. Run with an approved migration role in a new TEST database.
-- This is CMX-owned schema, NOT a full SAP DDIC clone. No production grants are supplied.
-- btree_gist must be approved by the database administrator.
BEGIN;
CREATE EXTENSION IF NOT EXISTS btree_gist;
CREATE SCHEMA cmx_fnd;
CREATE TABLE cmx_fnd.client_scope (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL CHECK(mandt ~ '^[0-9]{3}$'),
 PRIMARY KEY(tenant_id,mandt));
CREATE TABLE cmx_fnd.foundation_release (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 release_id uuid NOT NULL, version integer NOT NULL CHECK(version>0),
 status text NOT NULL CHECK(status IN ('DRAFT','VALIDATED','APPROVED','PUBLISHED')),
 profile text NOT NULL, content_hash varchar(64), created_by text NOT NULL,
 approved_by text, approved_at timestamptz, published_at timestamptz,
 CHECK(content_hash IS NULL OR content_hash ~ '^[0-9a-f]{64}$'),
 CHECK(status NOT IN ('APPROVED','PUBLISHED') OR (approved_by IS NOT NULL AND approved_by<>created_by)),
 CHECK(status<>'PUBLISHED' OR (content_hash IS NOT NULL AND published_at IS NOT NULL)),
 UNIQUE(tenant_id,mandt,version),
 PRIMARY KEY (tenant_id, mandt, release_id),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt)
);
CREATE TABLE cmx_fnd.config_head (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 active_release_id uuid NOT NULL, version bigint NOT NULL DEFAULT 1 CHECK(version>0),
 PRIMARY KEY (tenant_id, mandt, active_release_id),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, active_release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id), UNIQUE(tenant_id,mandt)
);
CREATE TABLE cmx_fnd.company_key (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 bukrs varchar(4) NOT NULL CHECK(length(bukrs)>0), object_id uuid NOT NULL, UNIQUE(tenant_id,mandt,object_id),
 PRIMARY KEY (tenant_id, mandt, bukrs),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt)
);
CREATE TABLE cmx_fnd.valuation_area_key (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 bwkey varchar(4) NOT NULL CHECK(length(bwkey)>0), object_id uuid NOT NULL, UNIQUE(tenant_id,mandt,object_id),
 PRIMARY KEY (tenant_id, mandt, bwkey),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt)
);
CREATE TABLE cmx_fnd.plant_key (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 werks varchar(4) NOT NULL CHECK(length(werks)>0), object_id uuid NOT NULL, UNIQUE(tenant_id,mandt,object_id),
 PRIMARY KEY (tenant_id, mandt, werks),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt)
);
CREATE TABLE cmx_fnd.purchasing_org_key (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 ekorg varchar(4) NOT NULL CHECK(length(ekorg)>0), object_id uuid NOT NULL, UNIQUE(tenant_id,mandt,object_id),
 PRIMARY KEY (tenant_id, mandt, ekorg),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt)
);
CREATE TABLE cmx_fnd.sales_org_key (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 vkorg varchar(4) NOT NULL CHECK(length(vkorg)>0), object_id uuid NOT NULL, UNIQUE(tenant_id,mandt,object_id),
 PRIMARY KEY (tenant_id, mandt, vkorg),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt)
);
CREATE TABLE cmx_fnd.controlling_area_key (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 kokrs varchar(4) NOT NULL CHECK(length(kokrs)>0), object_id uuid NOT NULL, UNIQUE(tenant_id,mandt,object_id),
 PRIMARY KEY (tenant_id, mandt, kokrs),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt)
);
CREATE TABLE cmx_fnd.ledger_key (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 rldnr varchar(2) NOT NULL CHECK(length(rldnr)>0), object_id uuid NOT NULL, UNIQUE(tenant_id,mandt,object_id),
 PRIMARY KEY (tenant_id, mandt, rldnr),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt)
);
CREATE TABLE cmx_fnd.currency_config (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 release_id uuid NOT NULL, currency varchar(5) NOT NULL, minor_units smallint NOT NULL CHECK(minor_units BETWEEN 0 AND 8),
 PRIMARY KEY (tenant_id, mandt, release_id, currency),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id)
);
CREATE TABLE cmx_fnd.uom_config (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 release_id uuid NOT NULL, unit varchar(3) NOT NULL, dimension text NOT NULL, quantity_decimals smallint NOT NULL CHECK(quantity_decimals BETWEEN 0 AND 9),
 PRIMARY KEY (tenant_id, mandt, release_id, unit),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id)
);
CREATE TABLE cmx_fnd.fiscal_variant_config (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 release_id uuid NOT NULL, periv varchar(2) NOT NULL, calendar_kind text NOT NULL CHECK(calendar_kind IN ('CALENDAR','SHIFTED','EXPLICIT')), original_t009 jsonb,
 PRIMARY KEY (tenant_id, mandt, release_id, periv),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id)
);
CREATE TABLE cmx_fnd.fiscal_year_config (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 release_id uuid NOT NULL, periv varchar(2) NOT NULL, gjahr integer NOT NULL CHECK(gjahr BETWEEN 1 AND 9999),
 normal_periods smallint NOT NULL CHECK(normal_periods BETWEEN 1 AND 366),
 special_periods smallint NOT NULL CHECK(special_periods BETWEEN 0 AND 16),
 date_from date NOT NULL, date_to date NOT NULL CHECK(date_to>date_from),
 EXCLUDE USING gist (tenant_id WITH =,mandt WITH =,release_id WITH =,periv WITH =,daterange(date_from,date_to,'[)') WITH &&),
 PRIMARY KEY (tenant_id, mandt, release_id, periv, gjahr),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id),
 FOREIGN KEY (tenant_id, mandt, release_id, periv) REFERENCES cmx_fnd.fiscal_variant_config (tenant_id, mandt, release_id, periv)
);
CREATE TABLE cmx_fnd.fiscal_period_config (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 release_id uuid NOT NULL, periv varchar(2) NOT NULL, gjahr integer NOT NULL, poper smallint NOT NULL CHECK(poper>0),
 date_from date NOT NULL, date_to date NOT NULL CHECK(date_to>date_from),
 EXCLUDE USING gist (tenant_id WITH =,mandt WITH =,release_id WITH =,periv WITH =,daterange(date_from,date_to,'[)') WITH &&),
 PRIMARY KEY (tenant_id, mandt, release_id, periv, gjahr, poper),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id),
 FOREIGN KEY (tenant_id, mandt, release_id, periv, gjahr) REFERENCES cmx_fnd.fiscal_year_config (tenant_id, mandt, release_id, periv, gjahr)
);
CREATE TABLE cmx_fnd.posting_variant_config (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 release_id uuid NOT NULL, opvar varchar(4) NOT NULL,
 PRIMARY KEY (tenant_id, mandt, release_id, opvar),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id)
);
CREATE TABLE cmx_fnd.company_config (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 release_id uuid NOT NULL, bukrs varchar(4) NOT NULL, name text NOT NULL, country varchar(3) NOT NULL,
 currency varchar(5) NOT NULL, ktopl varchar(4) NOT NULL, periv varchar(2) NOT NULL,
 opvar varchar(4) NOT NULL, time_zone text NOT NULL,
 PRIMARY KEY (tenant_id, mandt, release_id, bukrs),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id),
 FOREIGN KEY (tenant_id, mandt, bukrs) REFERENCES cmx_fnd.company_key (tenant_id, mandt, bukrs), FOREIGN KEY (tenant_id, mandt, release_id, currency) REFERENCES cmx_fnd.currency_config (tenant_id, mandt, release_id, currency), FOREIGN KEY (tenant_id, mandt, release_id, periv) REFERENCES cmx_fnd.fiscal_variant_config (tenant_id, mandt, release_id, periv), FOREIGN KEY (tenant_id, mandt, release_id, opvar) REFERENCES cmx_fnd.posting_variant_config (tenant_id, mandt, release_id, opvar)
);
CREATE TABLE cmx_fnd.valuation_area_config (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 release_id uuid NOT NULL, bwkey varchar(4) NOT NULL, bukrs varchar(4) NOT NULL, bwmod varchar(4) NOT NULL DEFAULT '',
 PRIMARY KEY (tenant_id, mandt, release_id, bwkey),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id),
 FOREIGN KEY (tenant_id, mandt, bwkey) REFERENCES cmx_fnd.valuation_area_key (tenant_id, mandt, bwkey), FOREIGN KEY (tenant_id, mandt, release_id, bukrs) REFERENCES cmx_fnd.company_config (tenant_id, mandt, release_id, bukrs)
);
CREATE TABLE cmx_fnd.plant_config (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 release_id uuid NOT NULL, werks varchar(4) NOT NULL, bwkey varchar(4) NOT NULL, name text NOT NULL, time_zone text NOT NULL, factory_calendar text,
 PRIMARY KEY (tenant_id, mandt, release_id, werks),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id),
 FOREIGN KEY (tenant_id, mandt, werks) REFERENCES cmx_fnd.plant_key (tenant_id, mandt, werks), FOREIGN KEY (tenant_id, mandt, release_id, bwkey) REFERENCES cmx_fnd.valuation_area_config (tenant_id, mandt, release_id, bwkey)
);
CREATE TABLE cmx_fnd.storage_location_config (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 release_id uuid NOT NULL, werks varchar(4) NOT NULL, lgort varchar(4) NOT NULL, name text NOT NULL,
 PRIMARY KEY (tenant_id, mandt, release_id, werks, lgort),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id),
 FOREIGN KEY (tenant_id, mandt, release_id, werks) REFERENCES cmx_fnd.plant_config (tenant_id, mandt, release_id, werks)
);
CREATE TABLE cmx_fnd.purchasing_org_config (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 release_id uuid NOT NULL, ekorg varchar(4) NOT NULL, bukrs varchar(4), name text NOT NULL,
 PRIMARY KEY (tenant_id, mandt, release_id, ekorg),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id),
 FOREIGN KEY (tenant_id, mandt, ekorg) REFERENCES cmx_fnd.purchasing_org_key (tenant_id, mandt, ekorg), FOREIGN KEY (tenant_id, mandt, release_id, bukrs) REFERENCES cmx_fnd.company_config (tenant_id, mandt, release_id, bukrs)
);
CREATE TABLE cmx_fnd.purchasing_plant_config (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 release_id uuid NOT NULL, werks varchar(4) NOT NULL, ekorg varchar(4) NOT NULL,
 PRIMARY KEY (tenant_id, mandt, release_id, werks, ekorg),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id),
 FOREIGN KEY (tenant_id, mandt, release_id, werks) REFERENCES cmx_fnd.plant_config (tenant_id, mandt, release_id, werks), FOREIGN KEY (tenant_id, mandt, release_id, ekorg) REFERENCES cmx_fnd.purchasing_org_config (tenant_id, mandt, release_id, ekorg)
);
CREATE TABLE cmx_fnd.controlling_assignment_config (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 release_id uuid NOT NULL, bukrs varchar(4) NOT NULL, gsber varchar(4) NOT NULL DEFAULT '', kokrs varchar(4) NOT NULL,
 PRIMARY KEY (tenant_id, mandt, release_id, bukrs, gsber),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id),
 FOREIGN KEY (tenant_id, mandt, release_id, bukrs) REFERENCES cmx_fnd.company_config (tenant_id, mandt, release_id, bukrs), FOREIGN KEY (tenant_id, mandt, kokrs) REFERENCES cmx_fnd.controlling_area_key (tenant_id, mandt, kokrs)
);
CREATE TABLE cmx_fnd.sales_org_config (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 release_id uuid NOT NULL, vkorg varchar(4) NOT NULL, bukrs varchar(4) NOT NULL,
 PRIMARY KEY (tenant_id, mandt, release_id, vkorg),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id),
 FOREIGN KEY (tenant_id, mandt, vkorg) REFERENCES cmx_fnd.sales_org_key (tenant_id, mandt, vkorg), FOREIGN KEY (tenant_id, mandt, release_id, bukrs) REFERENCES cmx_fnd.company_config (tenant_id, mandt, release_id, bukrs)
);
CREATE TABLE cmx_fnd.sales_area_config (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 release_id uuid NOT NULL, vkorg varchar(4) NOT NULL, vtweg varchar(2) NOT NULL, spart varchar(2) NOT NULL,
 PRIMARY KEY (tenant_id, mandt, release_id, vkorg, vtweg, spart),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id),
 FOREIGN KEY (tenant_id, mandt, release_id, vkorg) REFERENCES cmx_fnd.sales_org_config (tenant_id, mandt, release_id, vkorg)
);
CREATE TABLE cmx_fnd.sales_plant_config (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 release_id uuid NOT NULL, vkorg varchar(4) NOT NULL, vtweg varchar(2) NOT NULL, werks varchar(4) NOT NULL,
 PRIMARY KEY (tenant_id, mandt, release_id, vkorg, vtweg, werks),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id),
 FOREIGN KEY (tenant_id, mandt, release_id, vkorg) REFERENCES cmx_fnd.sales_org_config (tenant_id, mandt, release_id, vkorg), FOREIGN KEY (tenant_id, mandt, release_id, werks) REFERENCES cmx_fnd.plant_config (tenant_id, mandt, release_id, werks)
);
CREATE TABLE cmx_fnd.ledger_config (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 release_id uuid NOT NULL, rldnr varchar(2) NOT NULL, ledger_kind text NOT NULL CHECK(ledger_kind IN ('STANDARD','EXTENSION','TECHNICAL')),
 leading boolean NOT NULL, valuation_view text NOT NULL, default_principle text,
 PRIMARY KEY (tenant_id, mandt, release_id, rldnr),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id),
 FOREIGN KEY (tenant_id, mandt, rldnr) REFERENCES cmx_fnd.ledger_key (tenant_id, mandt, rldnr)
);
CREATE TABLE cmx_fnd.book_config (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 release_id uuid NOT NULL, bukrs varchar(4) NOT NULL, rldnr varchar(2) NOT NULL, periv varchar(2) NOT NULL, opvar varchar(4) NOT NULL,
 accounting_principle text NOT NULL, functional_currency_type varchar(2) NOT NULL,
 required_for_inventory boolean NOT NULL DEFAULT false,
 inventory_capability text NOT NULL CHECK(inventory_capability IN ('DESIGN_ONLY','IMPLEMENTED_NOT_ENABLED','ENABLED_AND_VALIDATED')),
 price_method varchar(1) NOT NULL CHECK(price_method IN ('S','V')),
 active_from date NOT NULL, active_to date, CHECK(active_to IS NULL OR active_to>active_from),
 PRIMARY KEY (tenant_id, mandt, release_id, bukrs, rldnr),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id),
 FOREIGN KEY (tenant_id, mandt, release_id, bukrs) REFERENCES cmx_fnd.company_config (tenant_id, mandt, release_id, bukrs), FOREIGN KEY (tenant_id, mandt, release_id, rldnr) REFERENCES cmx_fnd.ledger_config (tenant_id, mandt, release_id, rldnr), FOREIGN KEY (tenant_id, mandt, release_id, periv) REFERENCES cmx_fnd.fiscal_variant_config (tenant_id, mandt, release_id, periv), FOREIGN KEY (tenant_id, mandt, release_id, opvar) REFERENCES cmx_fnd.posting_variant_config (tenant_id, mandt, release_id, opvar)
);
CREATE TABLE cmx_fnd.book_currency_config (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 release_id uuid NOT NULL, bukrs varchar(4) NOT NULL, rldnr varchar(2) NOT NULL, external_currency_type varchar(2) NOT NULL,
 internal_currency_type varchar(2) NOT NULL, currency varchar(5) NOT NULL,
 source_slot varchar(1), ml_relevant boolean NOT NULL,
 UNIQUE(tenant_id,mandt,release_id,bukrs,rldnr,internal_currency_type),
 PRIMARY KEY (tenant_id, mandt, release_id, bukrs, rldnr, external_currency_type),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id),
 FOREIGN KEY (tenant_id, mandt, release_id, bukrs, rldnr) REFERENCES cmx_fnd.book_config (tenant_id, mandt, release_id, bukrs, rldnr), FOREIGN KEY (tenant_id, mandt, release_id, currency) REFERENCES cmx_fnd.currency_config (tenant_id, mandt, release_id, currency)
);
ALTER TABLE cmx_fnd.book_config ADD CONSTRAINT book_functional_role_fk FOREIGN KEY (tenant_id, mandt, release_id, bukrs, rldnr, functional_currency_type) REFERENCES cmx_fnd.book_currency_config (tenant_id, mandt, release_id, bukrs, rldnr, external_currency_type) DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE cmx_fnd.posting_account_rule (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 release_id uuid NOT NULL, rule_id uuid NOT NULL, opvar varchar(4) NOT NULL,
 account_type varchar(1) NOT NULL CHECK(account_type IN ('+','A','D','K','M','S')),
 account_from varchar(10) COLLATE "C" NOT NULL DEFAULT '',
 account_to varchar(10) COLLATE "C" NOT NULL DEFAULT '', authorization_group text,
 CHECK((account_type='+' AND account_from='' AND account_to='') OR
       (account_type<>'+' AND account_from<>'' AND account_from<=account_to)),
 UNIQUE(tenant_id,mandt,release_id,opvar,account_type,account_to),
 PRIMARY KEY (tenant_id, mandt, release_id, rule_id),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id),
 FOREIGN KEY (tenant_id, mandt, release_id, opvar) REFERENCES cmx_fnd.posting_variant_config (tenant_id, mandt, release_id, opvar)
);
CREATE TABLE cmx_fnd.posting_window (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 release_id uuid NOT NULL, rule_id uuid NOT NULL, interval_number smallint NOT NULL CHECK(interval_number BETWEEN 1 AND 3),
 from_year integer NOT NULL CHECK(from_year BETWEEN 1 AND 9999), from_period smallint NOT NULL CHECK(from_period BETWEEN 1 AND 366),
 to_year integer NOT NULL CHECK(to_year BETWEEN 1 AND 9999), to_period smallint NOT NULL CHECK(to_period BETWEEN 1 AND 366),
 CHECK((from_year,from_period)<=(to_year,to_period)),
 PRIMARY KEY (tenant_id, mandt, release_id, rule_id, interval_number),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id),
 FOREIGN KEY (tenant_id, mandt, release_id, rule_id) REFERENCES cmx_fnd.posting_account_rule (tenant_id, mandt, release_id, rule_id)
);
CREATE TABLE cmx_fnd.master_identity (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 object_id uuid NOT NULL, object_type text NOT NULL, business_key text NOT NULL,
 UNIQUE(tenant_id,mandt,object_id,object_type), UNIQUE(tenant_id,mandt,object_type,business_key),
 PRIMARY KEY (tenant_id, mandt, object_id),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt)
);
CREATE TABLE cmx_fnd.external_key_map (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 source_system text NOT NULL, source_client text NOT NULL, object_type text NOT NULL,
 external_key text NOT NULL, object_id uuid NOT NULL,
 PRIMARY KEY (tenant_id, mandt, source_system, source_client, object_type, external_key),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id)
);
CREATE TABLE cmx_fnd.bp_identity (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 partner_guid uuid NOT NULL, partner varchar(10) NOT NULL, object_id uuid NOT NULL,
 object_type text NOT NULL DEFAULT 'BP' CHECK(object_type='BP'), UNIQUE(tenant_id,mandt,partner),
 PRIMARY KEY (tenant_id, mandt, partner_guid),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id)
);
CREATE TABLE cmx_fnd.customer_link (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 kunnr varchar(10) NOT NULL, partner_guid uuid NOT NULL, UNIQUE(tenant_id,mandt,partner_guid),
 PRIMARY KEY (tenant_id, mandt, kunnr),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id)
);
CREATE TABLE cmx_fnd.supplier_link (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 lifnr varchar(10) NOT NULL, partner_guid uuid NOT NULL, UNIQUE(tenant_id,mandt,partner_guid),
 PRIMARY KEY (tenant_id, mandt, lifnr),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id)
);
CREATE TABLE cmx_fnd.bp_role_version (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 revision_id uuid NOT NULL, partner_guid uuid NOT NULL, role varchar(6) NOT NULL, dfval varchar(1) NOT NULL DEFAULT '',
 valid_from timestamptz NOT NULL, valid_to timestamptz,
 recorded_from timestamptz NOT NULL, recorded_to timestamptz,
 approved_change_id uuid NOT NULL,
 CHECK(valid_to IS NULL OR valid_to>valid_from),
 CHECK(recorded_to IS NULL OR recorded_to>recorded_from),
 EXCLUDE USING gist (tenant_id WITH =,mandt WITH =,partner_guid WITH =, role WITH =, dfval WITH =,
 tstzrange(valid_from,valid_to,'[)') WITH &&,
 tstzrange(recorded_from,recorded_to,'[)') WITH &&),
 PRIMARY KEY (tenant_id, mandt, revision_id),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, partner_guid) REFERENCES cmx_fnd.bp_identity (tenant_id, mandt, partner_guid)
);
CREATE TABLE cmx_fnd.customer_company_version (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 revision_id uuid NOT NULL, kunnr varchar(10) NOT NULL, bukrs varchar(4) NOT NULL, akont varchar(10) NOT NULL,
 zterm varchar(4), posting_block boolean NOT NULL, payment_block text,
 valid_from date NOT NULL, valid_to date,
 recorded_from timestamptz NOT NULL, recorded_to timestamptz,
 approved_change_id uuid NOT NULL,
 CHECK(valid_to IS NULL OR valid_to>valid_from),
 CHECK(recorded_to IS NULL OR recorded_to>recorded_from),
 EXCLUDE USING gist (tenant_id WITH =,mandt WITH =,kunnr WITH =, bukrs WITH =,
 daterange(valid_from,valid_to,'[)') WITH &&,
 tstzrange(recorded_from,recorded_to,'[)') WITH &&),
 PRIMARY KEY (tenant_id, mandt, revision_id),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, kunnr) REFERENCES cmx_fnd.customer_link (tenant_id, mandt, kunnr), FOREIGN KEY (tenant_id, mandt, bukrs) REFERENCES cmx_fnd.company_key (tenant_id, mandt, bukrs)
);
CREATE TABLE cmx_fnd.supplier_company_version (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 revision_id uuid NOT NULL, lifnr varchar(10) NOT NULL, bukrs varchar(4) NOT NULL, akont varchar(10) NOT NULL,
 zterm varchar(4), posting_block boolean NOT NULL, payment_block text,
 valid_from date NOT NULL, valid_to date,
 recorded_from timestamptz NOT NULL, recorded_to timestamptz,
 approved_change_id uuid NOT NULL,
 CHECK(valid_to IS NULL OR valid_to>valid_from),
 CHECK(recorded_to IS NULL OR recorded_to>recorded_from),
 EXCLUDE USING gist (tenant_id WITH =,mandt WITH =,lifnr WITH =, bukrs WITH =,
 daterange(valid_from,valid_to,'[)') WITH &&,
 tstzrange(recorded_from,recorded_to,'[)') WITH &&),
 PRIMARY KEY (tenant_id, mandt, revision_id),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, lifnr) REFERENCES cmx_fnd.supplier_link (tenant_id, mandt, lifnr), FOREIGN KEY (tenant_id, mandt, bukrs) REFERENCES cmx_fnd.company_key (tenant_id, mandt, bukrs)
);
CREATE TABLE cmx_fnd.customer_sales_version (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 revision_id uuid NOT NULL, kunnr varchar(10) NOT NULL, vkorg varchar(4) NOT NULL, vtweg varchar(2) NOT NULL,
 spart varchar(2) NOT NULL, order_block text, delivery_block text, billing_block text,
 currency varchar(5), payment_terms varchar(4),
 valid_from date NOT NULL, valid_to date,
 recorded_from timestamptz NOT NULL, recorded_to timestamptz,
 approved_change_id uuid NOT NULL,
 CHECK(valid_to IS NULL OR valid_to>valid_from),
 CHECK(recorded_to IS NULL OR recorded_to>recorded_from),
 EXCLUDE USING gist (tenant_id WITH =,mandt WITH =,kunnr WITH =, vkorg WITH =, vtweg WITH =, spart WITH =,
 daterange(valid_from,valid_to,'[)') WITH &&,
 tstzrange(recorded_from,recorded_to,'[)') WITH &&),
 PRIMARY KEY (tenant_id, mandt, revision_id),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, kunnr) REFERENCES cmx_fnd.customer_link (tenant_id, mandt, kunnr), FOREIGN KEY (tenant_id, mandt, vkorg) REFERENCES cmx_fnd.sales_org_key (tenant_id, mandt, vkorg)
);
CREATE TABLE cmx_fnd.supplier_purchasing_version (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 revision_id uuid NOT NULL, lifnr varchar(10) NOT NULL, ekorg varchar(4) NOT NULL,
 purchasing_block boolean NOT NULL, order_currency varchar(5), payment_terms varchar(4),
 valid_from date NOT NULL, valid_to date,
 recorded_from timestamptz NOT NULL, recorded_to timestamptz,
 approved_change_id uuid NOT NULL,
 CHECK(valid_to IS NULL OR valid_to>valid_from),
 CHECK(recorded_to IS NULL OR recorded_to>recorded_from),
 EXCLUDE USING gist (tenant_id WITH =,mandt WITH =,lifnr WITH =, ekorg WITH =,
 daterange(valid_from,valid_to,'[)') WITH &&,
 tstzrange(recorded_from,recorded_to,'[)') WITH &&),
 PRIMARY KEY (tenant_id, mandt, revision_id),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, lifnr) REFERENCES cmx_fnd.supplier_link (tenant_id, mandt, lifnr), FOREIGN KEY (tenant_id, mandt, ekorg) REFERENCES cmx_fnd.purchasing_org_key (tenant_id, mandt, ekorg)
);
CREATE TABLE cmx_fnd.material_identity (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 matnr varchar(40) NOT NULL, object_id uuid NOT NULL, object_type text NOT NULL DEFAULT 'MATERIAL' CHECK(object_type='MATERIAL'),
 PRIMARY KEY (tenant_id, mandt, matnr),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id)
);
CREATE TABLE cmx_fnd.material_version (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 revision_id uuid NOT NULL, matnr varchar(40) NOT NULL, base_unit varchar(3) NOT NULL, material_type varchar(4) NOT NULL,
 sku varchar(100), quantity_decimals smallint NOT NULL CHECK(quantity_decimals BETWEEN 0 AND 9),
 valid_from date NOT NULL, valid_to date,
 recorded_from timestamptz NOT NULL, recorded_to timestamptz,
 approved_change_id uuid NOT NULL,
 CHECK(valid_to IS NULL OR valid_to>valid_from),
 CHECK(recorded_to IS NULL OR recorded_to>recorded_from),
 EXCLUDE USING gist (tenant_id WITH =,mandt WITH =,matnr WITH =,
 daterange(valid_from,valid_to,'[)') WITH &&,
 tstzrange(recorded_from,recorded_to,'[)') WITH &&),
 PRIMARY KEY (tenant_id, mandt, revision_id),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, matnr) REFERENCES cmx_fnd.material_identity (tenant_id, mandt, matnr)
);
CREATE TABLE cmx_fnd.material_plant_version (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 revision_id uuid NOT NULL, matnr varchar(40) NOT NULL, werks varchar(4) NOT NULL,
 kokrs varchar(4), prctr varchar(10), status_code text,
 valid_from date NOT NULL, valid_to date,
 recorded_from timestamptz NOT NULL, recorded_to timestamptz,
 approved_change_id uuid NOT NULL,
 CHECK(valid_to IS NULL OR valid_to>valid_from),
 CHECK(recorded_to IS NULL OR recorded_to>recorded_from),
 EXCLUDE USING gist (tenant_id WITH =,mandt WITH =,matnr WITH =, werks WITH =,
 daterange(valid_from,valid_to,'[)') WITH &&,
 tstzrange(recorded_from,recorded_to,'[)') WITH &&),
 PRIMARY KEY (tenant_id, mandt, revision_id),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, matnr) REFERENCES cmx_fnd.material_identity (tenant_id, mandt, matnr), FOREIGN KEY (tenant_id, mandt, werks) REFERENCES cmx_fnd.plant_key (tenant_id, mandt, werks)
);
CREATE TABLE cmx_fnd.material_uom_version (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 revision_id uuid NOT NULL, matnr varchar(40) NOT NULL, alternative_unit varchar(3) NOT NULL,
 numerator numeric(31,9) NOT NULL CHECK(numerator>0 AND numerator<>'NaN'::numeric),
 denominator numeric(31,9) NOT NULL CHECK(denominator>0 AND denominator<>'NaN'::numeric),
 valid_from date NOT NULL, valid_to date,
 recorded_from timestamptz NOT NULL, recorded_to timestamptz,
 approved_change_id uuid NOT NULL,
 CHECK(valid_to IS NULL OR valid_to>valid_from),
 CHECK(recorded_to IS NULL OR recorded_to>recorded_from),
 EXCLUDE USING gist (tenant_id WITH =,mandt WITH =,matnr WITH =, alternative_unit WITH =,
 daterange(valid_from,valid_to,'[)') WITH &&,
 tstzrange(recorded_from,recorded_to,'[)') WITH &&),
 PRIMARY KEY (tenant_id, mandt, revision_id),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, matnr) REFERENCES cmx_fnd.material_identity (tenant_id, mandt, matnr)
);
CREATE TABLE cmx_fnd.gl_account_version (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 revision_id uuid NOT NULL, ktopl varchar(4) NOT NULL, saknr varchar(10) NOT NULL,
 account_category text NOT NULL, description text NOT NULL,
 valid_from date NOT NULL, valid_to date,
 recorded_from timestamptz NOT NULL, recorded_to timestamptz,
 approved_change_id uuid NOT NULL,
 CHECK(valid_to IS NULL OR valid_to>valid_from),
 CHECK(recorded_to IS NULL OR recorded_to>recorded_from),
 EXCLUDE USING gist (tenant_id WITH =,mandt WITH =,ktopl WITH =, saknr WITH =,
 daterange(valid_from,valid_to,'[)') WITH &&,
 tstzrange(recorded_from,recorded_to,'[)') WITH &&),
 PRIMARY KEY (tenant_id, mandt, revision_id),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt)
);
CREATE TABLE cmx_fnd.gl_company_version (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 revision_id uuid NOT NULL, bukrs varchar(4) NOT NULL, saknr varchar(10) NOT NULL,
 reconciliation_type varchar(1) CHECK(reconciliation_type IN ('D','K','A')),
 currency varchar(5) NOT NULL, open_item_managed boolean NOT NULL,
 posting_block boolean NOT NULL, automatic_postings_only boolean NOT NULL,
 valid_from date NOT NULL, valid_to date,
 recorded_from timestamptz NOT NULL, recorded_to timestamptz,
 approved_change_id uuid NOT NULL,
 CHECK(valid_to IS NULL OR valid_to>valid_from),
 CHECK(recorded_to IS NULL OR recorded_to>recorded_from),
 EXCLUDE USING gist (tenant_id WITH =,mandt WITH =,bukrs WITH =, saknr WITH =,
 daterange(valid_from,valid_to,'[)') WITH &&,
 tstzrange(recorded_from,recorded_to,'[)') WITH &&),
 PRIMARY KEY (tenant_id, mandt, revision_id),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, bukrs) REFERENCES cmx_fnd.company_key (tenant_id, mandt, bukrs)
);
CREATE TABLE cmx_fnd.profit_center_version (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 revision_id uuid NOT NULL, kokrs varchar(4) NOT NULL, prctr varchar(10) NOT NULL, name text NOT NULL, segment text,
 valid_from date NOT NULL, valid_to date,
 recorded_from timestamptz NOT NULL, recorded_to timestamptz,
 approved_change_id uuid NOT NULL,
 CHECK(valid_to IS NULL OR valid_to>valid_from),
 CHECK(recorded_to IS NULL OR recorded_to>recorded_from),
 EXCLUDE USING gist (tenant_id WITH =,mandt WITH =,kokrs WITH =, prctr WITH =,
 daterange(valid_from,valid_to,'[)') WITH &&,
 tstzrange(recorded_from,recorded_to,'[)') WITH &&),
 PRIMARY KEY (tenant_id, mandt, revision_id),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, kokrs) REFERENCES cmx_fnd.controlling_area_key (tenant_id, mandt, kokrs)
);
CREATE TABLE cmx_fnd.profit_company_version (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 revision_id uuid NOT NULL, kokrs varchar(4) NOT NULL, prctr varchar(10) NOT NULL, bukrs varchar(4) NOT NULL,
 valid_from date NOT NULL, valid_to date,
 recorded_from timestamptz NOT NULL, recorded_to timestamptz,
 approved_change_id uuid NOT NULL,
 CHECK(valid_to IS NULL OR valid_to>valid_from),
 CHECK(recorded_to IS NULL OR recorded_to>recorded_from),
 EXCLUDE USING gist (tenant_id WITH =,mandt WITH =,kokrs WITH =, prctr WITH =, bukrs WITH =,
 daterange(valid_from,valid_to,'[)') WITH &&,
 tstzrange(recorded_from,recorded_to,'[)') WITH &&),
 PRIMARY KEY (tenant_id, mandt, revision_id),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, kokrs) REFERENCES cmx_fnd.controlling_area_key (tenant_id, mandt, kokrs), FOREIGN KEY (tenant_id, mandt, bukrs) REFERENCES cmx_fnd.company_key (tenant_id, mandt, bukrs)
);
CREATE TABLE cmx_fnd.cost_center_version (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 revision_id uuid NOT NULL, kokrs varchar(4) NOT NULL, kostl varchar(10) NOT NULL,
 bukrs varchar(4) NOT NULL, prctr varchar(10), source_datbi varchar(8), name text NOT NULL,
 valid_from date NOT NULL, valid_to date,
 recorded_from timestamptz NOT NULL, recorded_to timestamptz,
 approved_change_id uuid NOT NULL,
 CHECK(valid_to IS NULL OR valid_to>valid_from),
 CHECK(recorded_to IS NULL OR recorded_to>recorded_from),
 EXCLUDE USING gist (tenant_id WITH =,mandt WITH =,kokrs WITH =, kostl WITH =,
 daterange(valid_from,valid_to,'[)') WITH &&,
 tstzrange(recorded_from,recorded_to,'[)') WITH &&),
 PRIMARY KEY (tenant_id, mandt, revision_id),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, kokrs) REFERENCES cmx_fnd.controlling_area_key (tenant_id, mandt, kokrs), FOREIGN KEY (tenant_id, mandt, bukrs) REFERENCES cmx_fnd.company_key (tenant_id, mandt, bukrs)
);
CREATE TABLE cmx_fnd.valuation_unit (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 kalnr varchar(12) NOT NULL, matnr varchar(40) NOT NULL, bwkey varchar(4) NOT NULL,
 bwtar varchar(10) NOT NULL DEFAULT '', sobkz varchar(1) NOT NULL DEFAULT '',
 kdauf varchar(10) NOT NULL DEFAULT '', kdpos varchar(6) NOT NULL DEFAULT '',
 pspnr varchar(8) NOT NULL DEFAULT '', lifnr varchar(10) NOT NULL DEFAULT '',
 UNIQUE(tenant_id,mandt,matnr,bwkey,bwtar,sobkz,kdauf,kdpos,pspnr,lifnr),
 PRIMARY KEY (tenant_id, mandt, kalnr),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id)
);
CREATE TABLE cmx_fnd.material_price_version (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 revision_id uuid NOT NULL, kalnr varchar(12) NOT NULL, rldnr varchar(2) NOT NULL,
 external_currency_type varchar(2) NOT NULL, price_type varchar(20) NOT NULL,
 price_subtype varchar(20) NOT NULL DEFAULT '', currency varchar(5) NOT NULL, valuation_unit varchar(3) NOT NULL,
 numerator numeric(38,18) NOT NULL CHECK(numerator>=0 AND numerator<>'NaN'::numeric),
 denominator numeric(38,18) NOT NULL CHECK(denominator>0 AND denominator<>'NaN'::numeric),
 raw_price numeric(38,18), raw_price_unit numeric(18,0), source_reference jsonb NOT NULL DEFAULT '{}'::jsonb,
 valid_from date NOT NULL, valid_to date,
 recorded_from timestamptz NOT NULL, recorded_to timestamptz,
 approved_change_id uuid NOT NULL,
 CHECK(valid_to IS NULL OR valid_to>valid_from),
 CHECK(recorded_to IS NULL OR recorded_to>recorded_from),
 EXCLUDE USING gist (tenant_id WITH =,mandt WITH =,kalnr WITH =, rldnr WITH =, external_currency_type WITH =, price_type WITH =, price_subtype WITH =,
 daterange(valid_from,valid_to,'[)') WITH &&,
 tstzrange(recorded_from,recorded_to,'[)') WITH &&),
 PRIMARY KEY (tenant_id, mandt, revision_id),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, kalnr) REFERENCES cmx_fnd.valuation_unit (tenant_id, mandt, kalnr), FOREIGN KEY (tenant_id, mandt, rldnr) REFERENCES cmx_fnd.ledger_key (tenant_id, mandt, rldnr)
);
CREATE TABLE cmx_fnd.fx_rate_version (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 revision_id uuid NOT NULL, rate_type varchar(4) NOT NULL, from_currency varchar(5) NOT NULL, to_currency varchar(5) NOT NULL,
 normalized_multiplier numeric(38,18) NOT NULL CHECK(normalized_multiplier>0 AND normalized_multiplier<>'NaN'::numeric),
 quotation_source text NOT NULL, raw_source jsonb NOT NULL, normalization_profile text NOT NULL,
 valid_from date NOT NULL, valid_to date,
 recorded_from timestamptz NOT NULL, recorded_to timestamptz,
 approved_change_id uuid NOT NULL,
 CHECK(valid_to IS NULL OR valid_to>valid_from),
 CHECK(recorded_to IS NULL OR recorded_to>recorded_from),
 EXCLUDE USING gist (tenant_id WITH =,mandt WITH =,rate_type WITH =, from_currency WITH =, to_currency WITH =,
 daterange(valid_from,valid_to,'[)') WITH &&,
 tstzrange(recorded_from,recorded_to,'[)') WITH &&),
 PRIMARY KEY (tenant_id, mandt, revision_id),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt)
);
CREATE TABLE cmx_fnd.period_gate (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 bukrs varchar(4) NOT NULL, rldnr varchar(2) NOT NULL, gjahr integer NOT NULL CHECK(gjahr BETWEEN 1 AND 9999),
 poper smallint NOT NULL CHECK(poper BETWEEN 1 AND 382), application text NOT NULL,
 status text NOT NULL CHECK(status IN ('OPEN','CLOSING','CLOSED','HARD_CLOSED')),
 version bigint NOT NULL CHECK(version>0), changed_at timestamptz NOT NULL,
 changed_by text NOT NULL, approved_change_id uuid,
 PRIMARY KEY (tenant_id, mandt, bukrs, rldnr, gjahr, poper, application),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id)
);
CREATE TABLE cmx_fnd.action_block (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 object_id uuid NOT NULL, organization_key text NOT NULL DEFAULT '', action text NOT NULL,
 blocked boolean NOT NULL, version bigint NOT NULL CHECK(version>0), reason text,
 changed_at timestamptz NOT NULL,
 PRIMARY KEY (tenant_id, mandt, object_id, organization_key, action),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id)
);
CREATE TABLE cmx_fnd.command_receipt (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 source_system text NOT NULL, action text NOT NULL, idempotency_key text NOT NULL,
 request_hash varchar(64) NOT NULL CHECK(request_hash ~ '^[0-9a-f]{64}$'),
 state text NOT NULL CHECK(state IN ('STARTED','COMPLETED')), result jsonb,
 created_at timestamptz NOT NULL, completed_at timestamptz,
 PRIMARY KEY (tenant_id, mandt, source_system, action, idempotency_key),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt)
);
CREATE TABLE cmx_fnd.outbox (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 event_id uuid NOT NULL, aggregate_key text NOT NULL, aggregate_version bigint NOT NULL,
 event_type text NOT NULL, payload jsonb NOT NULL, created_at timestamptz NOT NULL,
 state text NOT NULL CHECK(state IN ('PENDING','LEASED','DONE','DEAD')),
 attempt integer NOT NULL DEFAULT 0 CHECK(attempt>=0), available_at timestamptz NOT NULL,
 lease_until timestamptz, UNIQUE(tenant_id,mandt,aggregate_key,aggregate_version,event_type),
 PRIMARY KEY (tenant_id, mandt, event_id),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt)
);
CREATE TABLE cmx_fnd.context_snapshot (
 tenant_id uuid NOT NULL, mandt varchar(3) NOT NULL,
 context_id uuid NOT NULL, release_id uuid NOT NULL, request_hash varchar(64) NOT NULL,
 payload jsonb NOT NULL, created_at timestamptz NOT NULL, expires_at timestamptz NOT NULL,
 subject_id text NOT NULL, CHECK(expires_at>created_at),
 PRIMARY KEY (tenant_id, mandt, context_id),
 FOREIGN KEY (tenant_id, mandt) REFERENCES cmx_fnd.client_scope (tenant_id, mandt),
 FOREIGN KEY (tenant_id, mandt, release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id)
);

-- Always write the canonical schema migration under a privileged deployer.
-- No grant to a generic metadata-save role, browser, plugin or AI SQL executor.
CREATE FUNCTION cmx_fnd.prevent_published_config_mutation() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,cmx_fnd AS $$
DECLARE s text; t uuid; c varchar(3); r uuid;
BEGIN
 IF TG_OP='INSERT' THEN t:=NEW.tenant_id; c:=NEW.mandt; r:=NEW.release_id;
 ELSE t:=OLD.tenant_id; c:=OLD.mandt; r:=OLD.release_id; END IF;
 IF TG_OP='UPDATE' AND (NEW.tenant_id,NEW.mandt,NEW.release_id) IS DISTINCT FROM (OLD.tenant_id,OLD.mandt,OLD.release_id) THEN
  RAISE EXCEPTION 'FND_CONFIG_KEY_IMMUTABLE';
 END IF;
 SELECT status INTO s FROM cmx_fnd.foundation_release
  WHERE tenant_id=t AND mandt=c AND release_id=r FOR SHARE;
 IF s IS NULL OR s='PUBLISHED' THEN RAISE EXCEPTION 'FND_RELEASE_IMMUTABLE_OR_MISSING'; END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END $$;
CREATE FUNCTION cmx_fnd.prevent_release_rewrite() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,cmx_fnd AS $$
BEGIN
 IF OLD.status='PUBLISHED' THEN RAISE EXCEPTION 'FND_PUBLISHED_RELEASE_IMMUTABLE'; END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END $$;
CREATE TRIGGER release_no_rewrite BEFORE UPDATE OR DELETE ON cmx_fnd.foundation_release
 FOR EACH ROW EXECUTE FUNCTION cmx_fnd.prevent_release_rewrite();
CREATE TRIGGER config_no_published_mutation BEFORE INSERT OR UPDATE OR DELETE ON cmx_fnd.currency_config FOR EACH ROW EXECUTE FUNCTION cmx_fnd.prevent_published_config_mutation();
CREATE TRIGGER config_no_published_mutation BEFORE INSERT OR UPDATE OR DELETE ON cmx_fnd.uom_config FOR EACH ROW EXECUTE FUNCTION cmx_fnd.prevent_published_config_mutation();
CREATE TRIGGER config_no_published_mutation BEFORE INSERT OR UPDATE OR DELETE ON cmx_fnd.fiscal_variant_config FOR EACH ROW EXECUTE FUNCTION cmx_fnd.prevent_published_config_mutation();
CREATE TRIGGER config_no_published_mutation BEFORE INSERT OR UPDATE OR DELETE ON cmx_fnd.fiscal_year_config FOR EACH ROW EXECUTE FUNCTION cmx_fnd.prevent_published_config_mutation();
CREATE TRIGGER config_no_published_mutation BEFORE INSERT OR UPDATE OR DELETE ON cmx_fnd.fiscal_period_config FOR EACH ROW EXECUTE FUNCTION cmx_fnd.prevent_published_config_mutation();
CREATE TRIGGER config_no_published_mutation BEFORE INSERT OR UPDATE OR DELETE ON cmx_fnd.posting_variant_config FOR EACH ROW EXECUTE FUNCTION cmx_fnd.prevent_published_config_mutation();
CREATE TRIGGER config_no_published_mutation BEFORE INSERT OR UPDATE OR DELETE ON cmx_fnd.company_config FOR EACH ROW EXECUTE FUNCTION cmx_fnd.prevent_published_config_mutation();
CREATE TRIGGER config_no_published_mutation BEFORE INSERT OR UPDATE OR DELETE ON cmx_fnd.valuation_area_config FOR EACH ROW EXECUTE FUNCTION cmx_fnd.prevent_published_config_mutation();
CREATE TRIGGER config_no_published_mutation BEFORE INSERT OR UPDATE OR DELETE ON cmx_fnd.plant_config FOR EACH ROW EXECUTE FUNCTION cmx_fnd.prevent_published_config_mutation();
CREATE TRIGGER config_no_published_mutation BEFORE INSERT OR UPDATE OR DELETE ON cmx_fnd.storage_location_config FOR EACH ROW EXECUTE FUNCTION cmx_fnd.prevent_published_config_mutation();
CREATE TRIGGER config_no_published_mutation BEFORE INSERT OR UPDATE OR DELETE ON cmx_fnd.purchasing_org_config FOR EACH ROW EXECUTE FUNCTION cmx_fnd.prevent_published_config_mutation();
CREATE TRIGGER config_no_published_mutation BEFORE INSERT OR UPDATE OR DELETE ON cmx_fnd.purchasing_plant_config FOR EACH ROW EXECUTE FUNCTION cmx_fnd.prevent_published_config_mutation();
CREATE TRIGGER config_no_published_mutation BEFORE INSERT OR UPDATE OR DELETE ON cmx_fnd.controlling_assignment_config FOR EACH ROW EXECUTE FUNCTION cmx_fnd.prevent_published_config_mutation();
CREATE TRIGGER config_no_published_mutation BEFORE INSERT OR UPDATE OR DELETE ON cmx_fnd.sales_org_config FOR EACH ROW EXECUTE FUNCTION cmx_fnd.prevent_published_config_mutation();
CREATE TRIGGER config_no_published_mutation BEFORE INSERT OR UPDATE OR DELETE ON cmx_fnd.sales_area_config FOR EACH ROW EXECUTE FUNCTION cmx_fnd.prevent_published_config_mutation();
CREATE TRIGGER config_no_published_mutation BEFORE INSERT OR UPDATE OR DELETE ON cmx_fnd.sales_plant_config FOR EACH ROW EXECUTE FUNCTION cmx_fnd.prevent_published_config_mutation();
CREATE TRIGGER config_no_published_mutation BEFORE INSERT OR UPDATE OR DELETE ON cmx_fnd.ledger_config FOR EACH ROW EXECUTE FUNCTION cmx_fnd.prevent_published_config_mutation();
CREATE TRIGGER config_no_published_mutation BEFORE INSERT OR UPDATE OR DELETE ON cmx_fnd.book_config FOR EACH ROW EXECUTE FUNCTION cmx_fnd.prevent_published_config_mutation();
CREATE TRIGGER config_no_published_mutation BEFORE INSERT OR UPDATE OR DELETE ON cmx_fnd.book_currency_config FOR EACH ROW EXECUTE FUNCTION cmx_fnd.prevent_published_config_mutation();
CREATE TRIGGER config_no_published_mutation BEFORE INSERT OR UPDATE OR DELETE ON cmx_fnd.posting_account_rule FOR EACH ROW EXECUTE FUNCTION cmx_fnd.prevent_published_config_mutation();
CREATE TRIGGER config_no_published_mutation BEFORE INSERT OR UPDATE OR DELETE ON cmx_fnd.posting_window FOR EACH ROW EXECUTE FUNCTION cmx_fnd.prevent_published_config_mutation();
CREATE TRIGGER config_no_published_mutation BEFORE INSERT OR UPDATE OR DELETE ON cmx_fnd.external_key_map FOR EACH ROW EXECUTE FUNCTION cmx_fnd.prevent_published_config_mutation();
CREATE TRIGGER config_no_published_mutation BEFORE INSERT OR UPDATE OR DELETE ON cmx_fnd.bp_identity FOR EACH ROW EXECUTE FUNCTION cmx_fnd.prevent_published_config_mutation();
CREATE TRIGGER config_no_published_mutation BEFORE INSERT OR UPDATE OR DELETE ON cmx_fnd.customer_link FOR EACH ROW EXECUTE FUNCTION cmx_fnd.prevent_published_config_mutation();
CREATE TRIGGER config_no_published_mutation BEFORE INSERT OR UPDATE OR DELETE ON cmx_fnd.supplier_link FOR EACH ROW EXECUTE FUNCTION cmx_fnd.prevent_published_config_mutation();
CREATE TRIGGER config_no_published_mutation BEFORE INSERT OR UPDATE OR DELETE ON cmx_fnd.material_identity FOR EACH ROW EXECUTE FUNCTION cmx_fnd.prevent_published_config_mutation();
CREATE TRIGGER config_no_published_mutation BEFORE INSERT OR UPDATE OR DELETE ON cmx_fnd.valuation_unit FOR EACH ROW EXECUTE FUNCTION cmx_fnd.prevent_published_config_mutation();
CREATE TRIGGER config_no_published_mutation BEFORE INSERT OR UPDATE OR DELETE ON cmx_fnd.period_gate FOR EACH ROW EXECUTE FUNCTION cmx_fnd.prevent_published_config_mutation();
CREATE TRIGGER config_no_published_mutation BEFORE INSERT OR UPDATE OR DELETE ON cmx_fnd.action_block FOR EACH ROW EXECUTE FUNCTION cmx_fnd.prevent_published_config_mutation();

-- Scope policies assume only the trusted service controls SET LOCAL app.tenant_id/app.mandt.
-- These settings are NOT a defence against an attacker who is handed arbitrary SQL
-- on the same connection. Do not expose raw SQL or the service role to plugins.
ALTER TABLE cmx_fnd.client_scope ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.client_scope FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.client_scope
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.foundation_release ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.foundation_release FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.foundation_release
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.config_head ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.config_head FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.config_head
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.company_key ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.company_key FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.company_key
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.valuation_area_key ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.valuation_area_key FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.valuation_area_key
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.plant_key ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.plant_key FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.plant_key
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.purchasing_org_key ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.purchasing_org_key FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.purchasing_org_key
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.sales_org_key ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.sales_org_key FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.sales_org_key
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.controlling_area_key ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.controlling_area_key FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.controlling_area_key
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.ledger_key ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.ledger_key FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.ledger_key
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.currency_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.currency_config FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.currency_config
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.uom_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.uom_config FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.uom_config
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.fiscal_variant_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.fiscal_variant_config FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.fiscal_variant_config
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.fiscal_year_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.fiscal_year_config FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.fiscal_year_config
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.fiscal_period_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.fiscal_period_config FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.fiscal_period_config
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.posting_variant_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.posting_variant_config FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.posting_variant_config
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.company_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.company_config FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.company_config
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.valuation_area_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.valuation_area_config FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.valuation_area_config
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.plant_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.plant_config FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.plant_config
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.storage_location_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.storage_location_config FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.storage_location_config
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.purchasing_org_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.purchasing_org_config FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.purchasing_org_config
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.purchasing_plant_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.purchasing_plant_config FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.purchasing_plant_config
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.controlling_assignment_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.controlling_assignment_config FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.controlling_assignment_config
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.sales_org_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.sales_org_config FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.sales_org_config
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.sales_area_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.sales_area_config FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.sales_area_config
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.sales_plant_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.sales_plant_config FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.sales_plant_config
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.ledger_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.ledger_config FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.ledger_config
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.book_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.book_config FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.book_config
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.book_currency_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.book_currency_config FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.book_currency_config
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.posting_account_rule ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.posting_account_rule FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.posting_account_rule
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.posting_window ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.posting_window FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.posting_window
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.master_identity ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.master_identity FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.master_identity
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.external_key_map ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.external_key_map FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.external_key_map
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.bp_identity ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.bp_identity FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.bp_identity
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.customer_link ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.customer_link FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.customer_link
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.supplier_link ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.supplier_link FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.supplier_link
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.bp_role_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.bp_role_version FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.bp_role_version
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.customer_company_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.customer_company_version FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.customer_company_version
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.supplier_company_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.supplier_company_version FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.supplier_company_version
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.customer_sales_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.customer_sales_version FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.customer_sales_version
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.supplier_purchasing_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.supplier_purchasing_version FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.supplier_purchasing_version
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.material_identity ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.material_identity FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.material_identity
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.material_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.material_version FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.material_version
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.material_plant_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.material_plant_version FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.material_plant_version
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.material_uom_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.material_uom_version FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.material_uom_version
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.gl_account_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.gl_account_version FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.gl_account_version
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.gl_company_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.gl_company_version FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.gl_company_version
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.profit_center_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.profit_center_version FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.profit_center_version
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.profit_company_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.profit_company_version FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.profit_company_version
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.cost_center_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.cost_center_version FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.cost_center_version
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.valuation_unit ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.valuation_unit FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.valuation_unit
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.material_price_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.material_price_version FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.material_price_version
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.fx_rate_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.fx_rate_version FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.fx_rate_version
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.period_gate ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.period_gate FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.period_gate
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.action_block ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.action_block FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.action_block
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.command_receipt ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.command_receipt FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.command_receipt
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.outbox ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.outbox FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.outbox
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
ALTER TABLE cmx_fnd.context_snapshot ENABLE ROW LEVEL SECURITY;
ALTER TABLE cmx_fnd.context_snapshot FORCE ROW LEVEL SECURITY;
CREATE POLICY scope_guard ON cmx_fnd.context_snapshot
 USING (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''))
 WITH CHECK (tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid AND mandt=nullif(current_setting('app.mandt',true),''));
COMMIT;
