from __future__ import annotations
import unittest
from copy import deepcopy
from datetime import date
from decimal import Decimal
from foundation import (Foundation, FoundationError, Scope, Period, choose_version, dec,
                        day, instant, half_open_sap_dates, convert_normalized_currency, code)
from demo_fixture import fixture, request, version

class FoundationTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture();self.req=request();self.now=instant("2026-09-14T12:00:00Z")
        self.scope=Scope(self.f["tenant_id"],"100","test-user")
        self.engine=Foundation(self.f,self.scope)
    def error(self, code_name, fn, *args, **kwargs):
        with self.assertRaises(FoundationError) as cm: fn(*args,**kwargs)
        self.assertEqual(cm.exception.code,code_name)
    def resolve(self):return self.engine.resolve_receipt(self.req,self.now)
    def test_01_plant_value_company_chain(self):
        r=self.resolve();self.assertEqual(r["organization"]["valuation_area"],"V100")
        self.assertEqual(r["organization"]["company"],"1000")
    def test_02_shared_quantity_not_ledger_sum(self):
        r=self.resolve();self.assertEqual(r["baseQuantity"],"60");self.assertEqual(len(r["books"]),2)
    def test_03_parallel_prices(self):
        r=self.resolve();self.assertEqual([b["currencyValues"][0]["amount"] for b in r["books"]],["6000.00","6300.00"])
    def test_04_external_currency_repeated_across_ledgers(self):
        r=self.resolve();self.assertEqual(r["books"][1]["currencyValues"][0]["currencyType"],"10")
        self.assertEqual(r["books"][1]["currencyValues"][0]["internalCurrencyType"],"A1")
    def test_05_company_hint_conflict(self):
        self.req["companyCode"]="2000";self.error("FND_ORG_SCOPE_MISMATCH",self.resolve)
    def test_06_missing_storage(self):
        self.req["storageLocation"]="9999";self.error("FND_STORAGE_NOT_ASSIGNED",self.resolve)
    def test_07_global_purchasing_needs_plant_link(self):
        self.f["purchasing_assignments"].remove(["1100","PG01"])
        self.error("FND_PURCHASING_NOT_ASSIGNED",self.engine.organization,"1100","0001","PG01")
    def test_08_cross_company_purchasing_allowed(self):
        r=self.engine.organization("2100","0001","PG01");self.assertEqual(r.company,"2000")
    def test_09_purchasing_company_mismatch(self):
        self.f["purchasing_assignments"].append(["2100","P100"])
        self.error("FND_PURCHASING_COMPANY_MISMATCH",self.engine.organization,"2100","0001","P100")
    def test_10_tka02_business_area_preserved(self):
        self.error("FND_CONTROLLING_ASSIGNMENT",self.engine.organization,"1100","0001","P100",business_area="0001")
    def test_11_tka02_duplicate_rejected(self):
        self.f["controlling_assignments"].append({"bukrs":"1000","gsber":"","kokrs":"B000"})
        self.error("FND_CONTROLLING_ASSIGNMENT",self.resolve)
    def test_12_sales_area_division_validated(self):
        self.error("FND_SALES_AREA_MISSING",self.engine.sales_assignment,"S100","10","99","1100")
    def test_13_sales_plant_assignment_not_division_keyed(self):
        self.engine.sales_assignment("S100","10","00","1100")
        self.engine.sales_assignment("S100","10","01","1100")
    def test_14_sales_plant_forbidden(self):
        self.error("FND_SALES_PLANT_NOT_ASSIGNED",self.engine.sales_assignment,"S100","10","00","2100")
    def test_15_bp_and_supplier_number_differ(self):
        self.assertTrue(self.resolve()["masterRevisions"])
    def test_16_missing_guid_mapping(self):
        self.f["supplier_links"].clear();self.error("FND_BP_LINK_MISSING",self.resolve)
    def test_17_missing_role(self):
        self.f["bp_roles"]=[];self.error("FND_BP_ROLE_MISSING_OR_AMBIGUOUS",self.resolve)
    def test_18_missing_purchasing_view(self):
        self.f["supplier_purchasing"]=[];self.error("FND_MASTER_VIEW_MISSING",self.resolve)
    def test_19_payment_block_does_not_prevent_receipt(self):
        self.f["current_supplier_blocks"]={"0000200001":["EXECUTE_PAYMENT"]};self.resolve()
    def test_20_receipt_block_enforced(self):
        self.f["current_supplier_blocks"]={"0000200001":["POST_GOODS_RECEIPT"]}
        self.error("FND_MASTER_ACTION_BLOCKED",self.resolve)
    def test_21_payment_requires_company_view(self):
        self.f["supplier_company"]=[]
        self.error("FND_MASTER_VIEW_MISSING",self.engine.validate_supplier,"0000200001","1000","P100",day("2026-09-14"),self.now,"EXECUTE_PAYMENT")
    def test_22_two_time_axes(self):
        rows=[version(key="C1",value="OLD",revision_id="R1",recorded_to="2026-10-05T00:00:00Z"),
              version(key="C1",value="NEW",revision_id="R2",valid_from="2026-10-01",recorded_from="2026-10-05T00:00:00Z")]
        self.assertEqual(choose_version(rows,day("2026-10-03"),instant("2026-10-03T12:00:00Z"),key="C1")["value"],"OLD")
        self.assertEqual(choose_version(rows,day("2026-10-03"),instant("2026-10-06T12:00:00Z"),key="C1")["value"],"NEW")
    def test_23_validity_end_exclusive(self):
        rows=[version(key="K",valid_to="2026-09-14")]
        self.error("FND_MASTER_VIEW_MISSING",choose_version,rows,day("2026-09-14"),self.now,key="K")
    def test_24_overlap_rejected(self):
        self.f["materials"].append(deepcopy(self.f["materials"][0]));self.error("FND_EFFECTIVITY_OVERLAP",self.resolve)
    def test_25_end_inclusive_date_adapter(self):
        self.assertEqual(half_open_sap_dates("20260101","20260131"),("2026-01-01","2026-02-01"))
    def test_26_maximum_date_not_incremented(self):
        self.assertEqual(half_open_sap_dates("20260101","99991231"),("2026-01-01",None))
    def test_27_zero_date_rejected(self):self.error("FND_DATE_INVALID",day,"0000-00-00")
    def test_28_invalid_calendar_date_rejected(self):self.error("FND_DATE_INVALID",day,"2026-02-30")
    def test_29_timestamp_needs_timezone(self):self.error("FND_TIMEZONE_REQUIRED",instant,"2026-09-14T12:00:00")
    def test_30_non_calendar_fiscal_year(self):
        r=self.engine.fiscal_period("A4",day("2027-01-15"));self.assertEqual((r.fiscal_year,r.period),(2026,10))
    def test_31_same_posting_date_different_ledger_periods(self):
        self.req["postingDate"]=self.req["valuationDate"]="2027-01-15"
        r=self.resolve();self.assertEqual([(b["fiscalYear"],b["period"]) for b in r["books"]],[(2027,1),(2026,10)])
    def test_32_special_period_is_explicit(self):
        self.assertEqual(self.engine.fiscal_period("K4",day("2026-12-31")).period,12)
    def test_33_special_period_13(self):
        self.assertEqual(self.engine.fiscal_period("K4",day("2026-12-31"),1).period,13)
    def test_34_special_period_not_last_period(self):
        self.error("FND_SPECIAL_PERIOD_INVALID",self.engine.fiscal_period,"K4",day("2026-09-30"),1)
    def test_35_special_period_limit(self):
        self.error("FND_SPECIAL_PERIOD_INVALID",self.engine.fiscal_period,"K4",day("2026-12-31"),5)
    def test_36_calendar_gap(self):
        self.error("FND_CALENDAR_GAP_OR_OVERLAP",self.engine.fiscal_period,"ZZ",day("2026-09-14"))
    def test_37_missing_period_header_rejected(self):
        self.f["period_rules"]=[];self.error("FND_PERIOD_HEADER_MISSING_OR_AMBIGUOUS",self.resolve)
    def test_38_no_account_range_inherits_header(self):
        self.engine.posting_window("P001",Period(2026,9,9,0),"S","0000400000")
    def test_39_account_specific_range_restricts(self):
        self.f["period_rules"].append({"opvar":"P001","account_type":"S","from_account":"0000400000","to_account":"0000499999","windows":[{"number":2,"from":[2026,10],"to":[2026,12]}]})
        self.error("FND_PERIOD_CLOSED",self.engine.posting_window,"P001",Period(2026,9,9,0),"S","0000400000")
    def test_40_interval_one_requires_group(self):
        self.f["period_rules"][0].update(authorization_group="CLOSE",windows=[{"number":1,"from":[2026,1],"to":[2026,16]}])
        self.error("FND_PERIOD_AUTHORIZATION",self.resolve)
        self.engine.resolve_receipt(self.req,self.now,{"CLOSE"})
    def test_41_interval_two_does_not_require_interval_one_group(self):
        self.f["period_rules"][0]["authorization_group"]="CLOSE";self.resolve()
    def test_42_cofi_interval_three(self):
        h=self.f["period_rules"][0];h["windows"].append({"number":3,"from":[2026,10],"to":[2026,12]})
        self.error("FND_PERIOD_CLOSED",self.engine.posting_window,"P001",Period(2026,9,9,0),transaction="COFI")
    def test_43_opvar_not_company(self):
        self.assertEqual(self.resolve()["books"][0]["postingPeriodVariant"],"P001")
    def test_44_required_ledger_missing_price_rejects_whole_resolution(self):
        self.f["prices"]=[p for p in self.f["prices"] if p["ledger"]!="2L"]
        self.error("FND_PRICE_MISSING",self.resolve)
    def test_45_price_ambiguity(self):
        self.f["prices"].append(deepcopy(self.f["prices"][0]));self.error("FND_PRICE_AMBIGUOUS",self.resolve)
    def test_46_price_units_must_match(self):
        self.f["prices"][0]["unit"]="KG";self.error("FND_PRICE_UNIT_OR_CURRENCY_MISMATCH",self.resolve)
    def test_47_price_zero_denominator(self):
        self.f["prices"][0]["denominator"]="0";self.error("FND_PRICE_INVALID",self.resolve)
    def test_48_price_for_100_pieces(self):
        p={"numerator":"250","denominator":"100"}
        self.assertEqual(self.engine.amount(Decimal("60"),p,2),Decimal("150.00"))
    def test_49_price_type_not_arbitrary_fallback(self):
        self.f["prices"][0]["price_type"]="PLANNED";self.error("FND_PRICE_MISSING",self.resolve)
    def test_50_future_price_not_used(self):
        self.f["prices"][0]["valid_from"]="2027-01-01";self.error("FND_PRICE_MISSING",self.resolve)
    def test_51_unsupported_price_method_rejected(self):
        self.f["books"][0]["price_method"]="V";self.error("FND_CAPABILITY_NOT_IMPLEMENTED",self.resolve)
    def test_52_incomplete_inventory_ledger_rejected(self):
        self.f["books"][0]["inventory_capability"]="DESIGN_ONLY";self.error("FND_LEDGER_INTEGRATION_INCOMPLETE",self.resolve)
    def test_53_decimal_string_only(self):self.error("FND_DECIMAL_FORMAT",dec,0.1)
    def test_54_nonfinite_rejected(self):self.error("FND_DECIMAL_FORMAT",dec,"NaN")
    def test_55_decimal_scale_rejected(self):self.error("FND_DECIMAL_SCALE",dec,"1.0001",3)
    def test_56_decimal_overflow(self):self.error("FND_DECIMAL_OVERFLOW",dec,"1000",integer_digits=3)
    def test_57_normalized_fx(self):self.assertEqual(convert_normalized_currency("100","7.1",2),"710.00")
    def test_58_missing_fx_not_one(self):self.error("FND_DECIMAL_FORMAT",convert_normalized_currency,"100",None,2)
    def test_59_fx_zero_rejected(self):self.error("FND_EXCHANGE_RATE_INVALID",convert_normalized_currency,"100","0",2)
    def test_60_no_fractional_piece(self):
        self.req.update(quantity="0.1",unit="EA");self.error("FND_QUANTITY_PRECISION",self.resolve)
    def test_61_old_release_rejected(self):
        self.req["expectedRelease"]="OLD";self.error("FND_RELEASE_STALE",self.resolve)
    def test_62_gate_closed_after_resolve(self):
        r=self.resolve();self.f["gates"][r["gateVersions"][0]["key"]]["status"]="CLOSED"
        self.error("FND_PERIOD_GATE_STALE",self.engine.revalidate,r)
    def test_63_gate_version_changed(self):
        r=self.resolve();self.f["gates"][r["gateVersions"][0]["key"]]["version"]=2
        self.error("FND_PERIOD_GATE_STALE",self.engine.revalidate,r)
    def test_64_cross_tenant_rejected(self):self.error("FND_SCOPE_MISMATCH",Foundation,self.f,Scope("OTHER","100","U"))
    def test_65_client_payload_cannot_set_tenant(self):
        self.req["tenant_id"]="OTHER";self.error("FND_UNKNOWN_REQUEST_FIELD",self.resolve)
    def test_66_code_leading_zero_preserved(self):self.assertEqual(code("0000123456",10),"0000123456")
    def test_67_matnr40_not_truncated(self):self.assertEqual(code("M"*40,40),"M"*40)
    def test_68_matnr41_rejected(self):self.error("FND_CODE_INVALID",code,"M"*41,40)
    def test_69_quantity_positive(self):
        self.req["quantity"]="0";self.error("FND_QUANTITY_INVALID",self.resolve)
    def test_70_valuation_date_policy(self):
        self.req["valuationDate"]="2026-09-13";self.error("FND_VALUATION_DATE_POLICY",self.resolve)
    def test_71_hash_deterministic(self):self.assertEqual(self.resolve()["contextHash"],self.resolve()["contextHash"])
    def test_72_not_a_posting(self):self.assertEqual(self.resolve()["status"],"RESOLVED_NOT_POSTED")

if __name__=="__main__": unittest.main(verbosity=2)
