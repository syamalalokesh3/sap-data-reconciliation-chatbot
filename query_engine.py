from dataclasses import dataclass

import pandas as pd

from ai_translator import translate_with_ai
from nlp_parser import QueryIntent, parse_question
from reconciliation import reconcile
from analytics import material_summary, vendor_summary
from sql_validator import validate_read_only_sql


@dataclass
class QueryResult:
    answer: str
    evidence: pd.DataFrame
    intent: QueryIntent | None = None
    sql: str = ""
    verification: str = "? CLARIFICATION REQUIRED"

    def __post_init__(self) -> None:
        if self.sql:
            self.sql = validate_read_only_sql(self.sql)


def execute_question(question: str, po: pd.DataFrame, receipts: pd.DataFrame, previous: pd.DataFrame | None = None) -> QueryResult:
    intent = parse_question(question)
    if isinstance(intent, str):
        if "those" in question.lower() and previous is not None and not previous.empty:
            intent = QueryIntent("reconciliation", threshold=intent.threshold)
        else:
            ai_intent = translate_with_ai(question) if intent.startswith("I can currently") else None
            if ai_intent is None:
                return QueryResult(intent, pd.DataFrame(), verification="? CLARIFICATION REQUIRED")
            intent = ai_intent
    data = reconcile(po, receipts)
    evidence = data
    sql = "SELECT * FROM PO_DATA p LEFT JOIN GR_IR_DATA g ON p.PO_NUMBER = g.PO_NUMBER AND p.PO_ITEM = g.PO_ITEM;"

    if intent.operation == "lookup":
        evidence = data[data["PO_NUMBER"].eq(intent.po_number)]
        if evidence.empty:
            return QueryResult(f"PO {intent.po_number} was not found in the loaded data.", evidence, intent, sql, "✓ DATA VERIFIED")
        return QueryResult(_format_lookup(evidence.iloc[0]), evidence, intent, sql, "✓ DATA VERIFIED")
    if intent.operation == "filter":
        evidence = data[data["VENDOR_NAME"].str.contains(intent.vendor or "", case=False, na=False)]
        return QueryResult(f"I found {len(evidence)} PO line(s) for {intent.vendor}.", evidence, intent, sql, "✓ DATA VERIFIED")
    if intent.operation == "total_value":
        evidence = data if not intent.vendor else data[data["VENDOR_NAME"].str.contains(intent.vendor, case=False, na=False)]
        total = evidence["PO_VALUE"].sum()
        scope = f" for vendor {intent.vendor}" if intent.vendor else ""
        return QueryResult(f"The total PO value{scope} is {_money(total)}.", evidence, intent, "SELECT SUM(PO_VALUE) FROM PO_DATA;", "✓ DATA VERIFIED")
    if intent.operation == "count":
        evidence = data if not intent.vendor else data[data["VENDOR_NAME"].str.contains(intent.vendor, case=False, na=False)]
        return QueryResult(f"There are {len(evidence)} PO line(s) in the loaded data.", evidence, intent, "SELECT COUNT(*) FROM PO_DATA;", "✓ DATA VERIFIED")
    if intent.operation == "missing_invoice":
        evidence = data[data["HAS_GR"] & ~data["HAS_IR"]]
        return QueryResult(f"I found {len(evidence)} PO(s) with goods receipts but no invoice receipt.", evidence, intent, sql, "✓ DATA VERIFIED")
    if intent.operation == "reconciliation":
        evidence = data[data["UNMATCHED_QTY"].abs() > 0]
        if intent.threshold is not None:
            evidence = evidence[evidence["UNMATCHED_VALUE"] > intent.threshold]
            qualifier = f" above {_money(intent.threshold)}"
        else:
            qualifier = ""
        if previous is not None and "those" in question.lower():
            evidence = evidence[evidence["PO_NUMBER"].isin(previous["PO_NUMBER"])]
        return QueryResult(f"I found {len(evidence)} PO(s) with unmatched receipt value{qualifier}.", evidence, intent, "SELECT PO_NUMBER, ORDER_QTY, SUM(RECEIVED_QTY) FROM PO_DATA p LEFT JOIN GR_IR_DATA g ON p.PO_NUMBER = g.PO_NUMBER WHERE g.DOCUMENT_TYPE = 'GR' GROUP BY PO_NUMBER, ORDER_QTY;", "✓ DATA VERIFIED")
    if intent.operation == "explain":
        evidence = data[data["PO_NUMBER"].eq(intent.po_number)]
        if evidence.empty:
            return QueryResult(f"PO {intent.po_number} was not found in the loaded data.", evidence, intent, sql, "✓ DATA VERIFIED")
        row = evidence.iloc[0]
        return QueryResult(_format_lookup(row, explanation=True), evidence, intent, sql, "✓ DATA VERIFIED")
    if intent.operation == "top_vendor":
        summary = vendor_summary(data).head(1)
        return QueryResult(f"{summary.iloc[0]['VENDOR_NAME']} has the highest PO value at {_money(summary.iloc[0]['PO_VALUE'])}.", summary, intent, "SELECT VENDOR_NAME, SUM(PO_VALUE) FROM PO_DATA GROUP BY VENDOR_NAME ORDER BY SUM(PO_VALUE) DESC LIMIT 1;", "✓ DATA VERIFIED")
    if intent.operation == "top_unmatched_vendor":
        summary = vendor_summary(data).sort_values("UNMATCHED_VALUE", ascending=False).head(1)
        return QueryResult(f"{summary.iloc[0]['VENDOR_NAME']} has the highest unmatched value at {_money(summary.iloc[0]['UNMATCHED_VALUE'])}.", summary, intent, sql, "✓ DATA VERIFIED")
    if intent.operation == "top_material":
        summary = material_summary(data).head(1)
        return QueryResult(f"{summary.iloc[0]['MATERIAL_DESC']} has the highest PO value at {_money(summary.iloc[0]['PO_VALUE'])}.", summary, intent, sql, "✓ DATA VERIFIED")
    if intent.operation == "top_material_qty":
        summary = material_summary(data).sort_values("ORDER_QTY", ascending=False).head(1)
        return QueryResult(f"{summary.iloc[0]['MATERIAL_DESC']} has the highest ordered quantity at {summary.iloc[0]['ORDER_QTY']:g}.", summary, intent, sql, "✓ DATA VERIFIED")
    return QueryResult("The question could not be safely translated into a supported query.", pd.DataFrame(), intent, verification="? CLARIFICATION REQUIRED")


def _money(value: float) -> str:
    return f"${value:,.2f}" if value % 1 else f"${value:,.0f}"


def _format_lookup(row, explanation: bool = False) -> str:
    base = f"PO {row['PO_NUMBER']} has {row['ORDER_QTY']:g} units ordered and {row['RECEIVED_QTY']:g} units received."
    detail = f" Therefore, {row['UNMATCHED_QTY']:g} units remain unmatched. At a unit price of {_money(row['UNIT_PRICE'])}, the unmatched value is {_money(row['UNMATCHED_VALUE'])}."
    return base + detail if explanation else f"{base} Vendor: {row['VENDOR_NAME']}. PO value: {_money(row['PO_VALUE'])}."


def evidence_columns(frame: pd.DataFrame) -> pd.DataFrame:
    columns = ["PO_NUMBER", "VENDOR_NAME", "MATERIAL_DESC", "ORDER_QTY", "RECEIVED_QTY", "INVOICE_QTY", "UNMATCHED_QTY", "UNIT_PRICE", "UNMATCHED_VALUE", "MATCH_STATUS", "EXCEPTION_TYPES", "SEVERITY", "HAS_IR"]
    return frame[[column for column in columns if column in frame.columns]].rename(columns={"HAS_IR": "INVOICE_RECEIVED"})
