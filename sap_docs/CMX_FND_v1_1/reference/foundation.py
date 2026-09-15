"""CMX Foundation executable specification, independently implemented.

Python stdlib only. This is NOT an installed CMX service or a reimplementation
of every SAP edge case. All callers must pass server-authenticated Scope.
Amounts use Decimal strings. Dates are explicit; no wall-clock defaults.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal, localcontext, ROUND_HALF_UP, InvalidOperation
from typing import Any, Iterable
import hashlib
import json
import re

class FoundationError(ValueError):
    def __init__(self, code: str, **details: Any):
        self.code, self.details = code, details
        super().__init__(f"{code}: {details}")

def fail(code: str, **details: Any) -> None:
    raise FoundationError(code, **details)

def dec(value: str, scale: int = 18, integer_digits: int = 20) -> Decimal:
    if not isinstance(value, str) or not re.fullmatch(r"[+-]?\d+(?:\.\d+)?", value):
        fail("FND_DECIMAL_FORMAT", value=repr(value))
    result = Decimal(value)
    if not result.is_finite() or -result.as_tuple().exponent > scale:
        fail("FND_DECIMAL_SCALE", value=value, scale=scale)
    if result.copy_abs() >= Decimal(10) ** integer_digits:
        fail("FND_DECIMAL_OVERFLOW", value=value)
    return result

def day(value: str) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        fail("FND_DATE_INVALID", value=value)
    try:
        return date.fromisoformat(value)
    except ValueError:
        fail("FND_DATE_INVALID", value=value)

def instant(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        fail("FND_TIMESTAMP_INVALID", value=value)
    if result.tzinfo is None:
        fail("FND_TIMEZONE_REQUIRED")
    return result.astimezone(timezone.utc)

def code(value: str, maximum: int) -> str:
    # No ALPHA/MATN1 emulation: preserve validated external representation.
    if not isinstance(value, str) or not value or len(value) > maximum or value != value.strip():
        fail("FND_CODE_INVALID", value=value, maximum=maximum)
    return value

def contains(v: dict[str, Any], business_date: date, known_at: datetime) -> bool:
    return (day(v["valid_from"]) <= business_date
            and (v.get("valid_to") is None or business_date < day(v["valid_to"]))
            and instant(v["recorded_from"]) <= known_at
            and (v.get("recorded_to") is None or known_at < instant(v["recorded_to"])))

def choose_version(rows: Iterable[dict[str, Any]], business_date: date,
                   known_at: datetime, **key: Any) -> dict[str, Any]:
    matches = [r for r in rows if all(r.get(k) == v for k, v in key.items())
               and contains(r, business_date, known_at)]
    if not matches:
        fail("FND_MASTER_VIEW_MISSING", key=key, business_date=str(business_date))
    if len(matches) != 1:
        fail("FND_EFFECTIVITY_OVERLAP", key=key)
    return matches[0]

def half_open_sap_dates(start: str, end: str) -> tuple[str, str | None]:
    """Use ONLY for source fields whose end-inclusive DATE convention is verified.
    Never use for BUT100 timestamp roles or unknown price boundary semantics.
    """
    def convert(v: str) -> date:
        if not isinstance(v, str) or not re.fullmatch(r"\d{8}", v):
            fail("FND_SAP_DATE_INVALID", value=v)
        return day(v[:4] + "-" + v[4:6] + "-" + v[6:])
    a, b = convert(start), convert(end)
    if a > b:
        fail("FND_EFFECTIVITY_INVALID")
    return a.isoformat(), None if b == date.max else (b + timedelta(days=1)).isoformat()

@dataclass(frozen=True)
class Scope:
    tenant_id: str
    client: str
    subject: str

@dataclass(frozen=True)
class Organization:
    company: str
    plant: str
    valuation_area: str
    storage_location: str
    controlling_area: str
    purchasing_organization: str

@dataclass(frozen=True)
class Period:
    fiscal_year: int
    period: int
    normal_period: int
    adjustment_index: int

class Foundation:
    def __init__(self, fixture: dict[str, Any], scope: Scope):
        self.data = fixture
        self.scope = scope
        if (fixture["tenant_id"], fixture["client"]) != (scope.tenant_id, scope.client):
            fail("FND_SCOPE_MISMATCH")
        if fixture.get("release_status") != "PUBLISHED":
            fail("FND_RELEASE_NOT_PUBLISHED")

    def organization(self, plant: str, storage: str, purchasing: str,
                     company_hint: str | None = None, business_area: str = "") -> Organization:
        try:
            p = self.data["plants"][plant]
            v = self.data["valuation_areas"][p["bwkey"]]
            company = v["bukrs"]
            self.data["companies"][company]
        except KeyError as e:
            fail("FND_ORG_MISSING", reference=str(e))
        if company_hint is not None and company_hint != company:
            fail("FND_ORG_SCOPE_MISMATCH", given=company_hint, derived=company)
        if [plant, storage] not in self.data["storage_locations"]:
            fail("FND_STORAGE_NOT_ASSIGNED", plant=plant, storage=storage)
        po = self.data["purchasing_organizations"].get(purchasing)
        if po is None or [plant, purchasing] not in self.data["purchasing_assignments"]:
            fail("FND_PURCHASING_NOT_ASSIGNED")
        if po.get("bukrs") not in (None, "", company):
            fail("FND_PURCHASING_COMPANY_MISMATCH")
        # Exact TKA02 business-area scope; no undocumented fallback.
        ca = [r["kokrs"] for r in self.data["controlling_assignments"]
              if r["bukrs"] == company and r["gsber"] == business_area]
        if len(ca) != 1:
            fail("FND_CONTROLLING_ASSIGNMENT", company=company, business_area=business_area)
        return Organization(company, plant, p["bwkey"], storage, ca[0], purchasing)

    def sales_assignment(self, sales_org: str, channel: str, division: str, plant: str) -> None:
        if [sales_org, channel, division] not in self.data["sales_areas"]:
            fail("FND_SALES_AREA_MISSING")
        # TVKWZ has no division. Do not silently widen the TVTA validation.
        if [sales_org, channel, plant] not in self.data["sales_plant_assignments"]:
            fail("FND_SALES_PLANT_NOT_ASSIGNED")

    def fiscal_period(self, calendar: str, posting_date: date, adjustment_index: int = 0) -> Period:
        if isinstance(adjustment_index, bool) or not isinstance(adjustment_index, int) or adjustment_index < 0:
            fail("FND_SPECIAL_PERIOD_INVALID")
        rows = [p for p in self.data["periods"] if p["periv"] == calendar
                and day(p["date_from"]) <= posting_date < day(p["date_to"])]
        if len(rows) != 1:
            fail("FND_CALENDAR_GAP_OR_OVERLAP", calendar=calendar, posting_date=str(posting_date))
        row = rows[0]
        year = self.data["fiscal_years"].get(f"{calendar}/{row['year']}")
        if year is None:
            fail("FND_FISCAL_YEAR_MISSING")
        if adjustment_index and (row["period"] != year["normal_periods"]
                                 or adjustment_index > year["special_periods"]):
            # Intentional conservative policy: no silent period clipping across ledgers.
            fail("FND_SPECIAL_PERIOD_INVALID", calendar=calendar, adjustment_index=adjustment_index)
        return Period(row["year"], row["period"] + adjustment_index, row["period"], adjustment_index)

    @staticmethod
    def _window_open(rule: dict[str, Any], period: Period, groups: set[str], transaction: str) -> None:
        key = (period.fiscal_year, period.period)
        intervals = rule["windows"]
        hits = {w["number"] for w in intervals if tuple(w["from"]) <= key <= tuple(w["to"])}
        # Explicit supported COFI policy. Caller must perform header first.
        if transaction == "COFI" and rule["account_type"] == "+" and any(w["number"] == 3 for w in intervals):
            if 3 not in hits:
                fail("FND_PERIOD_CLOSED", interval=3)
            return
        if not ({1, 2} & hits):
            fail("FND_PERIOD_CLOSED")
        if 1 in hits and 2 not in hits and rule.get("authorization_group") not in (None, ""):
            if rule["authorization_group"] not in groups:
                fail("FND_PERIOD_AUTHORIZATION", group=rule["authorization_group"])

    def posting_window(self, opvar: str, period: Period, account_type: str = "+",
                       account: str = "", groups: set[str] | None = None,
                       transaction: str = "RFBU") -> None:
        groups = groups or set()
        rules = [r for r in self.data["period_rules"] if r["opvar"] == opvar]
        headers = [r for r in rules if r["account_type"] == "+"]
        if len(headers) != 1:
            fail("FND_PERIOD_HEADER_MISSING_OR_AMBIGUOUS", opvar=opvar)
        self._window_open(headers[0], period, groups, transaction)
        if account_type == "+":
            return
        if account_type not in {"A", "D", "K", "M", "S"} or not account:
            fail("FND_ACCOUNT_CONTEXT_INVALID")
        if transaction == "COFI" and any(w["number"] == 3 for w in headers[0]["windows"]):
            return
        selected = [r for r in rules if r["account_type"] == account_type
                    and r["from_account"] <= account <= r["to_account"]]
        if len(selected) > 1:
            fail("FND_PERIOD_ACCOUNT_RANGE_OVERLAP")
        # SAP read_t001b has no additional line restriction when no range exists.
        if selected:
            self._window_open(selected[0], period, groups, transaction)

    def validate_supplier(self, supplier: str, company: str, purchasing: str,
                          posting_date: date, known_at: datetime, action: str) -> list[str]:
        allowed = {"POST_GOODS_RECEIPT": "PURCHASING", "POST_SUPPLIER_INVOICE": "FINANCE",
                   "EXECUTE_PAYMENT": "FINANCE"}
        if action not in allowed:
            fail("FND_ACTION_NOT_SUPPORTED", action=action)
        guid = self.data["supplier_links"].get(supplier)
        if guid is None or guid not in self.data["business_partners"]:
            fail("FND_BP_LINK_MISSING")
        role_name = allowed[action]
        roles = [r for r in self.data["bp_roles"] if r["guid"] == guid and r["role"] == role_name
                 and instant(r["valid_from"]) <= known_at
                 and (r.get("valid_to") is None or known_at < instant(r["valid_to"]))]
        if len(roles) != 1:
            fail("FND_BP_ROLE_MISSING_OR_AMBIGUOUS")
        refs = [roles[0]["revision_id"]]
        if role_name == "PURCHASING":
            view = choose_version(self.data["supplier_purchasing"], posting_date, known_at,
                                  lifnr=supplier, ekorg=purchasing)
        else:
            view = choose_version(self.data["supplier_company"], posting_date, known_at,
                                  lifnr=supplier, bukrs=company)
        refs.append(view["revision_id"])
        if action in self.data["current_supplier_blocks"].get(supplier, []):
            fail("FND_MASTER_ACTION_BLOCKED", action=action)
        return refs

    def price(self, kalnr: str, ledger: str, currency_type: str, on: date, known_at: datetime,
              price_type: str = "STANDARD", price_subtype: str = "") -> dict[str, Any]:
        rows = [r for r in self.data["prices"] if all([
            r["kalnr"] == kalnr, r["ledger"] == ledger,
            r["external_currency_type"] == currency_type,
            r["price_type"] == price_type, r["price_subtype"] == price_subtype])
                and contains(r, on, known_at)]
        if not rows:
            fail("FND_PRICE_MISSING", ledger=ledger, currency_type=currency_type)
        if len(rows) > 1:
            fail("FND_PRICE_AMBIGUOUS", ledger=ledger)
        p = rows[0]
        numerator, denominator = dec(p["numerator"]), dec(p["denominator"])
        if numerator < 0 or denominator <= 0:
            fail("FND_PRICE_INVALID")
        return p

    @staticmethod
    def amount(quantity: Decimal, price: dict[str, Any], currency_decimals: int) -> Decimal:
        if not quantity.is_finite() or not (0 <= currency_decimals <= 8):
            fail("FND_AMOUNT_INVALID")
        with localcontext() as ctx:
            ctx.prec = 80
            denominator = dec(price["denominator"])
            if denominator <= 0:
                fail("FND_PRICE_INVALID")
            value = quantity * dec(price["numerator"]) / denominator
            quantum = Decimal(1).scaleb(-currency_decimals)
            result = value.quantize(quantum, rounding=ROUND_HALF_UP)
            if result.copy_abs() >= Decimal(10) ** 23:
                fail("FND_AMOUNT_OVERFLOW")
            return result

    def resolve_receipt(self, request: dict[str, Any], known_at: datetime,
                        authorization_groups: set[str] | None = None) -> dict[str, Any]:
        fields = {"requestId", "action", "expectedRelease", "postingDate", "valuationDate",
                  "plant", "storageLocation", "purchasingOrganization", "companyCode",
                  "businessArea", "supplier", "material", "valuationType", "quantity", "unit"}
        if set(request) - fields:
            fail("FND_UNKNOWN_REQUEST_FIELD", fields=sorted(set(request) - fields))
        required = fields - {"companyCode", "businessArea", "valuationType"}
        if not required <= set(request):
            fail("FND_REQUEST_FIELDS_MISSING", fields=sorted(required - set(request)))
        if request["action"] != "POST_GOODS_RECEIPT":
            fail("FND_ACTION_NOT_SUPPORTED")
        if request["expectedRelease"] != self.data["release_id"]:
            fail("FND_RELEASE_STALE")
        d, vd = day(request["postingDate"]), day(request["valuationDate"])
        # MVP policy requires same date. Broader flows need separately approved policy.
        if vd != d:
            fail("FND_VALUATION_DATE_POLICY")
        org = self.organization(code(request["plant"],4),code(request["storageLocation"],4),
                                code(request["purchasingOrganization"],4),request.get("companyCode"),
                                request.get("businessArea", ""))
        supplier_refs = self.validate_supplier(code(request["supplier"],10), org.company,
                  org.purchasing_organization, d, known_at, request["action"])
        matnr = code(request["material"],40)
        material = choose_version(self.data["materials"], d, known_at, matnr=matnr)
        plant_view = choose_version(self.data["material_plants"], d, known_at, matnr=matnr, werks=org.plant)
        if request["action"] in plant_view.get("blocked_actions", []):
            fail("FND_MASTER_ACTION_BLOCKED")
        quantity = dec(request["quantity"], scale=9, integer_digits=22)
        if quantity <= 0:
            fail("FND_QUANTITY_INVALID")
        with localcontext() as ctx:
            ctx.prec = 80
            unit = code(request["unit"],3)
            if unit == material["base_unit"]:
                base_quantity = quantity
                uom_revision = material["revision_id"]
            else:
                conv = choose_version(self.data["units"], d, known_at, matnr=matnr, unit=unit)
                denominator = dec(conv["denominator"])
                if denominator <= 0 or dec(conv["numerator"]) <= 0:
                    fail("FND_UNIT_RATIO_INVALID")
                base_quantity = quantity * dec(conv["numerator"]) / denominator
                uom_revision = conv["revision_id"]
            rounded = base_quantity.quantize(Decimal(1).scaleb(-material["quantity_decimals"]))
            if rounded != base_quantity:
                fail("FND_QUANTITY_PRECISION")
            base_quantity = rounded
        valuation_type = request.get("valuationType", "")
        units = [v for v in self.data["valuation_units"] if v["matnr"] == matnr
                 and v["bwkey"] == org.valuation_area and v["bwtar"] == valuation_type]
        if len(units) != 1:
            fail("FND_VALUATION_UNIT_MISSING_OR_AMBIGUOUS")
        vu = units[0]
        books = [b for b in self.data["books"] if b["company"] == org.company
                 and b["required_for_receipt"]]
        if not books:
            fail("FND_REQUIRED_LEDGER_MISSING")
        if len({b["ledger"] for b in books}) != len(books):
            fail("FND_LEDGER_AMBIGUOUS")
        out, gate_refs = [], []
        for book in sorted(books, key=lambda b:b["ledger"]):
            if book["inventory_capability"] != "ENABLED_AND_VALIDATED":
                fail("FND_LEDGER_INTEGRATION_INCOMPLETE", ledger=book["ledger"])
            if book["price_method"] != "S":
                fail("FND_CAPABILITY_NOT_IMPLEMENTED", method=book["price_method"])
            period = self.fiscal_period(book["calendar"],d)
            self.posting_window(book["opvar"],period,groups=authorization_groups)
            for application in ("FI", "MM"):
                gate_key = f"{org.company}/{book['ledger']}/{period.fiscal_year}/{period.period}/{application}"
                gate = self.data["gates"].get(gate_key)
                if gate is None or gate["status"] != "OPEN":
                    fail("FND_PERIOD_GATE_CLOSED", key=gate_key)
                gate_refs.append({"key":gate_key,"version":gate["version"]})
            role_values=[]
            seen=set()
            for role in book["currency_roles"]:
                if role["external_type"] in seen:
                    fail("FND_CURRENCY_ROLE_AMBIGUOUS")
                seen.add(role["external_type"])
                p=self.price(vu["kalnr"],book["ledger"],role["external_type"],vd,known_at)
                if p["currency"] != role["currency"] or p["unit"] != material["base_unit"]:
                    fail("FND_PRICE_UNIT_OR_CURRENCY_MISMATCH")
                value=self.amount(base_quantity,p,role["decimals"])
                role_values.append({"currencyType":role["external_type"],
                    "internalCurrencyType":role["internal_type"],"currency":role["currency"],
                    "amount":format(value,"f"),"priceRevision":p["revision_id"],
                    "priceNumerator":p["numerator"],"priceDenominator":p["denominator"],
                    "priceUnit":p["unit"]})
            if not seen or book["functional_currency_type"] not in seen:
                fail("FND_FUNCTIONAL_CURRENCY_ROLE_MISSING")
            out.append({"ledger":book["ledger"],"accountingPrinciple":book["principle"],
                "valuationView":book["valuation_view"],"fiscalYearVariant":book["calendar"],
                "fiscalYear":period.fiscal_year,"period":period.period,
                "postingPeriodVariant":book["opvar"],"currencyValues":role_values})
        result={"requestId":request["requestId"],"status":"RESOLVED_NOT_POSTED",
                "releaseId":self.data["release_id"],"knownAt":known_at.isoformat(),
                "organization":org.__dict__,"material":matnr,
                "inputQuantity":request["quantity"],"inputUnit":request["unit"],
                "baseQuantity":format(base_quantity,"f"),"baseUnit":material["base_unit"],
                "valuationObject":vu["kalnr"],"books":out,"gateVersions":gate_refs,
                "masterRevisions":supplier_refs+[material["revision_id"],plant_view["revision_id"],uom_revision]}
        canonical=json.dumps(result,ensure_ascii=False,sort_keys=True,separators=(",",":"))
        result["contextHash"]=hashlib.sha256(canonical.encode()).hexdigest()
        # A hash is not authentication, a signature or a commit permission.
        return result

    def revalidate(self, resolved: dict[str,Any]) -> None:
        """In-memory contract only. Production must lock real DB rows in the same
        transaction as the later business write; see db/003_locking.sql."""
        if resolved["releaseId"] != self.data["release_id"]:
            fail("FND_RELEASE_STALE")
        for ref in resolved["gateVersions"]:
            actual=self.data["gates"].get(ref["key"])
            if actual is None or actual["status"]!="OPEN" or actual["version"]!=ref["version"]:
                fail("FND_PERIOD_GATE_STALE",key=ref["key"])

def convert_normalized_currency(amount: str, multiplier: str, decimals: int) -> str:
    """Consumes an ALREADY normalized rate; never interprets raw TCURR directly.
    Raw SAP factor/quotation/decimal handling must be separately verified."""
    a,m=dec(amount),dec(multiplier)
    if m<=0 or not 0<=decimals<=8:
        fail("FND_EXCHANGE_RATE_INVALID")
    with localcontext() as ctx:
        ctx.prec=80
        return format((a*m).quantize(Decimal(1).scaleb(-decimals),rounding=ROUND_HALF_UP),"f")
