"""Synthetic data only: not copied from the connected SAP client."""
from datetime import date

def version(**values):
    return {"valid_from":"2025-01-01","valid_to":None,
            "recorded_from":"2025-01-01T00:00:00Z","recorded_to":None,**values}

def fixture():
    periods=[]; years={}
    # Explicit date ranges are compiled output, not a YYYYMM fiscal shortcut.
    for fy in (2025,2026,2027):
        for periv,start_month in (("K4",1),("A4",4)):
            years[f"{periv}/{fy}"]={"normal_periods":12,"special_periods":4}
            for p in range(1,13):
                idx=fy*12+start_month-1+p-1
                y,m=divmod(idx,12); ey,em=divmod(idx+1,12)
                periods.append({"periv":periv,"year":fy,"period":p,
                                "date_from":date(y,m+1,1).isoformat(),
                                "date_to":date(ey,em+1,1).isoformat()})
    books=[];prices=[];gates={}
    for ledger,calendar,opvar,principle,prices_by_role in (
        ("0L","K4","P001","IFRS",{"10":"100.00","30":"14.00"}),
        ("2L","A4","P002","LOCAL",{"10":"105.00","30":"14.70"})):
        roles=[{"external_type":"10","internal_type":"10" if ledger=="0L" else "A1",
                "currency":"CNY","decimals":2},
               {"external_type":"30","internal_type":"30" if ledger=="0L" else "A2",
                "currency":"USD","decimals":2}]
        books.append({"company":"1000","ledger":ledger,"calendar":calendar,"opvar":opvar,
            "principle":principle,"valuation_view":"LEGAL","required_for_receipt":True,
            "inventory_capability":"ENABLED_AND_VALIDATED","price_method":"S",
            "functional_currency_type":"10","currency_roles":roles})
        for role in roles:
            prices.append(version(kalnr="V000001",ledger=ledger,
                external_currency_type=role["external_type"],price_type="STANDARD",price_subtype="",
                numerator=prices_by_role[role["external_type"]],denominator="1",
                currency=role["currency"],unit="EA",revision_id=f"PR-{ledger}-{role['external_type']}"))
        for fy in (2025,2026,2027):
            for p in range(1,17):
                for app in ("FI","MM"):
                    gates[f"1000/{ledger}/{fy}/{p}/{app}"]={"status":"OPEN","version":1}
    return {"tenant_id":"11111111-1111-1111-1111-111111111111","client":"100",
        "release_id":"22222222-2222-2222-2222-222222222222","release_status":"PUBLISHED",
        "companies":{"1000":{"ktopl":"YCOA"},"2000":{"ktopl":"YCOA"}},
        # Deliberately different plant and valuation-area codes.
        "plants":{"1100":{"bwkey":"V100"},"2100":{"bwkey":"V200"}},
        "valuation_areas":{"V100":{"bukrs":"1000"},"V200":{"bukrs":"2000"}},
        "storage_locations":[["1100","0001"],["2100","0001"]],
        "purchasing_organizations":{"P100":{"bukrs":"1000"},"PG01":{"bukrs":None}},
        "purchasing_assignments":[["1100","P100"],["1100","PG01"],["2100","PG01"]],
        "controlling_assignments":[{"bukrs":"1000","gsber":"","kokrs":"A000"},
                                   {"bukrs":"2000","gsber":"","kokrs":"A000"}],
        "sales_areas":[["S100","10","00"],["S100","10","01"]],
        "sales_plant_assignments":[["S100","10","1100"]],
        "periods":periods,"fiscal_years":years,
        "period_rules":[{"opvar":v,"account_type":"+","authorization_group":"",
            "windows":[{"number":2,"from":[2025,1],"to":[2027,16]}]} for v in ("P001","P002")],
        "business_partners":{"GUID-BP-A":{"partner":"BP000001"}},
        "supplier_links":{"0000200001":"GUID-BP-A"},
        "bp_roles":[{"guid":"GUID-BP-A","role":r,"valid_from":"2025-01-01T00:00:00Z",
                     "valid_to":None,"revision_id":f"BP-{r}"} for r in ("PURCHASING","FINANCE")],
        "supplier_purchasing":[version(lifnr="0000200001",ekorg="P100",revision_id="LFM1-1")],
        "supplier_company":[version(lifnr="0000200001",bukrs="1000",revision_id="LFB1-1")],
        "current_supplier_blocks":{},
        "materials":[version(matnr="CMX-MATERIAL-0001",base_unit="EA",quantity_decimals=0,revision_id="MARA-1")],
        "material_plants":[version(matnr="CMX-MATERIAL-0001",werks="1100",revision_id="MARC-1",blocked_actions=[])],
        "units":[version(matnr="CMX-MATERIAL-0001",unit="BOX",numerator="12",denominator="1",revision_id="MARM-1")],
        "valuation_units":[{"matnr":"CMX-MATERIAL-0001","bwkey":"V100","bwtar":"","kalnr":"V000001"}],
        "books":books,"prices":prices,"gates":gates}

def request():
    return {"requestId":"DEMO-GR-001","action":"POST_GOODS_RECEIPT",
        "expectedRelease":"22222222-2222-2222-2222-222222222222",
        "postingDate":"2026-09-14","valuationDate":"2026-09-14",
        "plant":"1100","storageLocation":"0001","purchasingOrganization":"P100",
        "companyCode":"1000","businessArea":"","supplier":"0000200001",
        "material":"CMX-MATERIAL-0001","valuationType":"","quantity":"5","unit":"BOX"}
