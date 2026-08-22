import pandas as pd

from config import severity_for


def reconcile(po: pd.DataFrame, receipts: pd.DataFrame) -> pd.DataFrame:
    gr = receipts[receipts["DOCUMENT_TYPE"].eq("GR")].groupby(
        ["PO_NUMBER", "PO_ITEM"], as_index=False
    )["RECEIVED_QTY"].sum()
    ir = receipts[receipts["DOCUMENT_TYPE"].eq("IR")].groupby(
        ["PO_NUMBER", "PO_ITEM"], as_index=False
    ).agg(INVOICE_QTY=("INVOICE_QTY", "sum"), IR_AMOUNT=("AMOUNT", "sum"))
    gr = receipts[receipts["DOCUMENT_TYPE"].eq("GR")].groupby(
        ["PO_NUMBER", "PO_ITEM"], as_index=False
    ).agg(RECEIVED_QTY=("RECEIVED_QTY", "sum"), GR_AMOUNT=("AMOUNT", "sum"))
    result = po.merge(gr, on=["PO_NUMBER", "PO_ITEM"], how="left")
    result = result.merge(ir, on=["PO_NUMBER", "PO_ITEM"], how="left")
    for column in ("RECEIVED_QTY", "INVOICE_QTY", "GR_AMOUNT", "IR_AMOUNT"):
        result[column] = result[column].fillna(0)
    result["UNMATCHED_QTY"] = result["ORDER_QTY"] - result["RECEIVED_QTY"]
    result["UNMATCHED_VALUE"] = result["UNMATCHED_QTY"] * result["UNIT_PRICE"]
    result["HAS_GR"] = result["RECEIVED_QTY"] > 0
    result["HAS_IR"] = result["INVOICE_QTY"] > 0
    result["EXCEPTION_TYPES"] = result.apply(_exception_types, axis=1)
    result["SEVERITY"] = result["UNMATCHED_VALUE"].map(severity_for)
    result["MATCH_STATUS"] = result.apply(_match_status, axis=1)
    return result


def _match_status(row) -> str:
    if not row["HAS_GR"]:
        return "NO GOODS RECEIPT"
    if not row["HAS_IR"]:
        return "INVOICE PENDING"
    if row["RECEIVED_QTY"] > row["ORDER_QTY"]:
        return "OVER RECEIPT"
    if row["INVOICE_QTY"] != row["RECEIVED_QTY"]:
        return "INVOICE MISMATCH"
    if row["RECEIVED_QTY"] < row["ORDER_QTY"]:
        return "PARTIAL RECEIPT"
    return "FULLY MATCHED"


def _exception_types(row) -> str:
    issues = []
    if not row["HAS_GR"]:
        issues.extend(["EX03 Missing Goods Receipt", "EX07 PO Has No GR"])
    if not row["HAS_IR"] and row["HAS_GR"]:
        issues.extend(["EX04 Missing Invoice Receipt", "EX08 PO Has No IR"])
    if row["RECEIVED_QTY"] != row["ORDER_QTY"]:
        issues.append("EX01 Quantity Mismatch")
    if row["RECEIVED_QTY"] > row["ORDER_QTY"]:
        issues.extend(["EX06 GR Greater Than PO", "EX10 Over Receipt"])
    if row["INVOICE_QTY"] > row["RECEIVED_QTY"]:
        issues.append("EX05 Invoice Greater Than GR")
    if row["IR_AMOUNT"] != row["GR_AMOUNT"] and row["HAS_IR"] and row["HAS_GR"]:
        issues.append("EX02 Amount Mismatch")
    return "; ".join(issues) or "None"
