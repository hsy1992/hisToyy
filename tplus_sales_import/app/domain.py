from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
import re
import json
from hashlib import sha256

CENT = Decimal("0.01")
REQUIRED_COLUMNS = ("仓库编码", "单据日期", "用友单号", "销售标识", "业务类型", "客户编码", "项目编码", "商品编码", "数量", "单价", "含税金额")


def decimal_value(value, name):
    try:
        number = Decimal(str(value).strip())
        if not number.is_finite():
            raise InvalidOperation
        return number
    except (InvalidOperation, ValueError):
        raise ValueError(name + "不是有效数值") from None


def money_parts(value, rate):
    with localcontext() as context:
        context.prec = 50
        gross = decimal_value(value, "含税金额")
        net = (gross / (1 + rate)).quantize(CENT, rounding=ROUND_HALF_UP)
        return gross, net, gross - net


def decimal_text(value):
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if Decimal(text) == 0 else text


def key(value):
    return str(value if value is not None else "").strip().casefold()


def valid_source_code(value):
    """ExternalCode is nvarchar(50): SQL Server counts UTF-16 code units."""
    if not value:
        return False
    try:
        return len(str(value).encode("utf-16-le")) <= 100
    except UnicodeError:
        return False


def original_row_fingerprint(row):
    # Physical workbook row numbers differ when a row is copied. Compare all
    # original input columns, excluding only the external location metadata.
    encoded = json.dumps(row.values, ensure_ascii=True, sort_keys=True, default=str).encode("utf-8")
    return sha256(encoded).digest()


def parse_rate(value):
    """Normalize enum Name: 13/13% are percentages; 0.13 is a ratio.

    Bare values from 1 through 100 are percentage points, including 1 (1%).
    The enum ID must never be passed in place of its Name.
    """
    text = str(value if value is not None else "").strip()
    if not text:
        raise ValueError("客户税率枚举缺失或名称为空")
    number = decimal_value(text[:-1] if text.endswith("%") else text, "税率枚举")
    if text.endswith("%") or number >= 1:
        number /= 100
    if not 0 <= number <= 1:
        raise ValueError("税率比例超出0至1范围")
    return number


def parse_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for pattern in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            pass
    raise ValueError("单据日期格式无效")


@dataclass
class SourceRow:
    number: int
    sheet: str
    values: dict
    status: str = "待处理"
    reasons: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    parsed: dict = field(default_factory=dict)
    sa_code: str = ""
    header_id: object = None

    @property
    def voucher(self):
        return str(self.values.get("用友单号", "")).strip()

    def reset(self):
        self.status = "待处理"
        self.reasons.clear()
        self.notes.clear()
        self.parsed.clear()
        self.sa_code = ""
        self.header_id = None


@dataclass
class Document:
    source: str
    rows: list
    code: str = ""

    @property
    def ready(self):
        return all(row.status == "待写入" for row in self.rows)


class MasterCache:
    def __init__(self, tables):
        self.tables = tables
        self.indexes = {}
        for name in ("customers", "inventory", "warehouse", "business", "project"):
            index = defaultdict(list)
            for record in tables[name]:
                index[key(record["code"])].append(record)
            self.indexes[name] = index
        self.units = {row["id"]: row for row in tables["unit"]}
        self.enums = {row["id"]: row for row in tables["tax"]}

    def match(self, table, code):
        label = {"customers": "客户", "inventory": "存货", "warehouse": "仓库", "business": "业务类型", "project": "项目"}[table]
        if not key(code):
            raise ValueError(label + "编码为空")
        candidates = self.indexes[table].get(key(code), [])
        if not candidates:
            raise ValueError(label + "编码不存在：" + str(code))
        if len(candidates) != 1:
            raise ValueError(label + "编码有多个候选：" + str(code))
        record = candidates[0]
        if record.get("disabled") not in (0, False):
            raise ValueError(label + "已停用或状态未知：" + str(code))
        return record


def validate_rows(rows, cache, stop, progress):
    documents = {}
    for index, row in enumerate(rows):
        if stop.is_set():
            break
        row.status = "校验中"
        parsed = row.parsed
        errors = row.reasons
        for name, action in (
            ("date", lambda: parse_date(row.values.get("单据日期"))),
            ("quantity", lambda: decimal_value(row.values.get("数量"), "数量")),
            ("price", lambda: decimal_value(row.values.get("单价"), "单价")),
            ("gross_source", lambda: decimal_value(row.values.get("含税金额"), "含税金额")),
        ):
            try:
                parsed[name] = action()
            except ValueError as exc:
                errors.append(str(exc))
        if not row.voucher:
            errors.append("源用友单号为空")
        elif not valid_source_code(row.voucher):
            errors.append("源用友单号超过50个数据库字符单位或含无效字符")
        for table, column in (("customers", "客户编码"), ("inventory", "商品编码"),
                              ("warehouse", "仓库编码"), ("business", "业务类型")):
            try:
                parsed[table] = cache.match(table, row.values.get(column))
            except ValueError as exc:
                errors.append(column + "：" + str(exc))
        try:
            project = cache.match("project", row.values.get("项目编码"))
            parsed["project_id"] = project["id"]
        except ValueError as exc:
            code = row.values.get("项目编码", "")
            if not key(code) or key(code) not in cache.indexes["project"]:
                parsed["project_id"] = None
                row.notes.append("项目未匹配留空：" + str(code))
            else:
                errors.append(str(exc))
        customer = parsed.get("customers")
        if customer:
            try:
                enum = cache.enums.get(customer.get("taxRate"), {})
                parsed["rate"] = parse_rate(enum.get("name"))
            except ValueError as exc:
                errors.append(f"客户税率ID {customer.get('taxRate')}：{exc}")
        inventory = parsed.get("inventory")
        if inventory:
            if inventory.get("isSingleUnit") != 1:
                errors.append("暂不支持多计量或计量状态未知的存货")
            unit = cache.units.get(inventory.get("idunit"))
            if not unit or unit.get("disabled") not in (0, False) or not unit.get("name"):
                errors.append("存货基本单位不存在、停用或名称为空")
            else:
                parsed["unit"] = unit
        business = parsed.get("business")
        if business and (key(business["code"]), business["id"]) not in (("15", 65), ("16", 66)):
            errors.append("业务类型映射与已确认的15→65、16→66不一致")
        if "rate" in parsed and "gross_source" in parsed:
            try:
                parsed["gross"], parsed["net"], parsed["tax"] = money_parts(parsed["gross_source"], parsed["rate"])
            except (InvalidOperation, ValueError):
                errors.append("金额计算超出可处理范围")
        if business and "quantity" in parsed:
            qty = parsed["quantity"]
            if (business["id"] == 65 and qty < 0) or (business["id"] == 66 and qty > 0):
                row.notes.append("数量正负与业务类型方向不同，请核对")
        row.status = "校验失败" if errors else "已校验"
        group_key = key(row.voucher) if row.voucher else f"__invalid_{index}"
        documents.setdefault(group_key, Document(row.voucher, [])).rows.append(row)
        if index % 500 == 0:
            progress("校验数据", index + 1, len(rows))
    for document in documents.values():
        signatures = {(row.parsed.get("date"),
                       key(row.values.get("客户编码")), key(row.values.get("业务类型")),
                       key(row.values.get("项目编码"))) for row in document.rows}
        conflict = len(signatures) != 1
        ids = [key(row.values.get("销售标识")) for row in document.rows]
        duplicate_line = len([v for v in ids if v]) != len(set(v for v in ids if v))
        originals, duplicate_originals = {}, set()
        for index, row in enumerate(document.rows):
            fingerprint = original_row_fingerprint(row)
            if fingerprint in originals:
                duplicate_originals.update((originals[fingerprint], index))
            else:
                originals[fingerprint] = index
        for index, row in enumerate(document.rows):
            if index in duplicate_originals:
                row.reasons.append("同一单据存在重复原始明细，未自动删行")
            if conflict:
                row.reasons.append("同一源单号的日期、客户、业务类型或项目不一致")
            if duplicate_line:
                row.reasons.append("同一单据有重复销售标识，未自动删行")
            if row.reasons:
                row.status = "校验失败"
        if any(row.reasons for row in document.rows):
            bad_lines = ",".join(f"{row.sheet}:{row.number}" for row in document.rows if row.reasons)
            for row in document.rows:
                if row.status != "校验失败":
                    row.status = "整单受阻"
                    row.reasons.append("同单问题行：" + bad_lines)
        else:
            for row in document.rows:
                row.status = "待写入"
    progress("校验数据", len(documents), len(documents))
    return list(documents.values())


def build_payload(document):
    first = document.rows[0].parsed
    now = datetime.now()
    header = dict(code=document.code, ExternalCode=document.source, ExternalVoucherCode=document.source,
                  pubuserdefnvc1="",
                  idcustomer=first["customers"]["id"], idsettlecustomer=first["customers"]["id"],
                  idproject=first["project_id"], idbusinesstype=first["business"]["id"],
                  maker="范立志", makerid=51,
                  # --- 原直接审核字段（已注释保留）：---
                  # auditor="范立志", auditorid=51, voucherState=189,
                  # ------------------------------------
                  # 未审核单据不插入审核人和审核时间字段。
                  # auditor="", auditorid=None,
                  voucherState=181,
                  agency="范立志", agencyid=51, isCarriedForwardOut=0,
                  idcurrency=4, idmarketingOrgan=1, iddepartment=None, idclerk=None, idrdstyle=24,
                  isAutoGenerateSaleOut=1, IsAutoSaleOut=1, isAutoGenerateInvoice=0,
                  invoiceType=281, reciveType=7, isCancel=428, isNoArapBookkeeping=0,
                  SaleInvoiceMedia=51014, DistributionMode=57419, saleInvoiceID=281,
                  LogisticsStatus=56134,
                  isCounteractDelivery=0, isPriceTrace=0, isBeforeSystemInuse=0,
                  iscarriedforwardin=0, ismodifiedcode=0, PrintCount=0,
                  IsSeparateByWareHouse=0, IsAutoWarehouse=0, SendInfoSource=0,
                  IsReadOnly=0, IsDigElectronicInvoice=0, IsOnlinePay=0,
                  # --- 原直接出库与审核时间（已注释保留）：---
                  # isSaleOut=15,
                  # auditeddate=first["date"], AuditedTime=now,
                  # ----------------------------------------
                  DataSource=2497, isSaleOut=305,  # 未出库枚举ID，非布尔值。
                  # auditeddate=None, AuditedTime=None,
                  voucherdate=first["date"], madedate=first["date"],
                  createdtime=now, updated=now, exchangeRate=Decimal(1),
                  discountRate=Decimal(1), discountAmount=Decimal(0), discountsAndAllowances=None,
                  origprereceiveamount=Decimal(0), PreReceiveAmount=Decimal(0),
                  origSettleAmount=Decimal(0), settleAmount=Decimal(0),
                  OrigInvoiceTaxAmount=Decimal(0), Allowances=Decimal(0),
                  origAllowances=Decimal(0), thisBalanceIntegral=Decimal(0),
                  origAmount=sum((row.parsed["net"] for row in document.rows), Decimal(0)),
                  origTaxAmount=sum((row.parsed["gross"] for row in document.rows), Decimal(0)))
    header["amount"] = header["origAmount"]
    header["taxAmount"] = header["origTaxAmount"]
    warehouses = {row.parsed["warehouse"]["id"] for row in document.rows}
    header["idwarehouse"] = next(iter(warehouses)) if len(warehouses) == 1 else None
    details = []
    for index, row in enumerate(document.rows):
        p = row.parsed
        with localcontext() as context:
            context.prec = 50
            # Zero-quantity returns remain valid; keep their source-price basis.
            price_basis = p["gross"] / p["quantity"] if p["quantity"] else p["price"]
            net_price = (price_basis / (1 + p["rate"])).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
        details.append(dict(code=f"{index:04d}", idinventory=p["inventory"]["id"],
                            idproject=p["project_id"], idbaseunit=p["unit"]["id"], idunit=p["unit"]["id"],
                            idwarehouse=p["warehouse"]["id"], quantity=p["quantity"], baseQuantity=p["quantity"],
                            # --- 原直接出库标记（已注释保留）：---
                            # saleOutQuantity=p["quantity"],
                            # isSaleOut=15,
                            # ------------------------------------
                            saleOutQuantity=Decimal(0),
                            compositionQuantity=decimal_text(p["quantity"]) + str(p["unit"]["name"]),
                            discountRate=Decimal(1), taxRate=p["rate"],
                            taxFlag=1, isModifiedPrice=1, DataSource=2497, isSaleOut=305,
                            RefundDifferenceFlag=51185,
                            isPresent=0, isManualCost=0, IsMemberIntegral=0,
                            IsPromotionPresent=0, DiscountPriceChange=0, TaxPriceChange=0,
                            origTaxPrice=p["price"], taxPrice=p["price"], origDiscountPrice=net_price,
                            discountPrice=net_price, origDiscountAmount=p["net"], discountAmount=p["net"],
                            origTax=p["tax"], tax=p["tax"], origTaxAmount=p["gross"], taxAmount=p["gross"],
                            priuserdefnvc2=row.voucher, priuserdefnvc3=str(row.values.get("销售标识", "")),
                            pubuserdefnvc1=row.voucher, pubuserdefnvc2=str(row.values.get("销售标识", "")),
                            createdtime=now, updated=now))
    return header, details


def build_arap_payloads(document, header_id, detail_id_map, now=None):
    if now is None:
        now = datetime.now()
    arap_records = []
    first = document.rows[0].parsed
    doc_date = first["date"]
    for index, row in enumerate(document.rows):
        p = row.parsed
        detail_id = detail_id_map.get((header_id, f"{index:04d}"))
        if detail_id is None:
            raise ValueError(f"未找到对应的存货明细ID：header={header_id}, line={index}")
        inv = p.get("inventory", {})
        rec = dict(
            year=doc_date.year,
            period=doc_date.month,
            voucherCode=document.code,
            businessCode=document.code,
            voucherID=header_id,
            businessID=header_id,
            voucherDetailID=detail_id,
            detailtype="inventory",
            detailID=inv.get("id"),
            detailCode=inv.get("code", ""),
            detailName=inv.get("name", ""),
            Detailspecification=inv.get("specification") or "",
            voucherDate=doc_date,
            registerDate=doc_date,
            idpartner=p["customers"]["id"],
            idnosettlepartner=p["customers"]["id"],
            idcurrency=4,
            exchangeRate=Decimal(1),
            idbusitype=p["business"]["id"],
            IdMarketingOrgan=1,
            idproject=p["project_id"],
            IdDetailProject=p["project_id"],
            Quantity=p["quantity"],
            TaxPrice=p["price"],
            OrigTaxPrice=p["price"],
            amount=p["gross"],
            origAmount=p["gross"],
            cashAmount=Decimal(0),
            origCashAmount=Decimal(0),
            settleAmount=Decimal(0),
            origSettleAmount=Decimal(0),
            inAllowances=Decimal(0),
            origInAllowances=Decimal(0),
            isArFlag=1,
            flag=-1,
            # 与销货单未审核状态一致，不标记为已审核。
            auditFlag=0,
            auditBussinessFlag=0,
            BookFlag=2212,
            bussinessFlag="0",
            DataSource=2497,
            RefundDifferenceFlag=51185,
            ExternalVoucherCode=document.source,
            detailPriuserdefnvc2=document.source,
            detailPriuserdefnvc3=str(row.values.get("销售标识", "")),
            headPubuserdefnvc1="",
            headPubuserdefnvc2="",
            OppositeSideVoucherID="",
            isCarriedForwardIn=0,
            isCarriedForwardOut=0,
            isRollInFlag=0,
            prepayFlag=0,
            idarapvouchertype=104,
            idvouchertype=104,
            vouchertimestamp=str(int(now.timestamp())),
            createdTime=now
        )
        arap_records.append(rec)
    return arap_records

