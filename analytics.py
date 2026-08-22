import pandas as pd


def kpis(data: pd.DataFrame, receipts: pd.DataFrame) -> dict[str, float]:
    return {
        "Total Purchase Orders": int(data["PO_NUMBER"].nunique()),
        "Total PO Value": float(data["PO_VALUE"].sum()),
        "Total Goods Receipts": int((receipts["DOCUMENT_TYPE"] == "GR").sum()),
        "Total Invoice Receipts": int((receipts["DOCUMENT_TYPE"] == "IR").sum()),
        "Matched POs": int((data["MATCH_STATUS"] == "FULLY MATCHED").sum()),
        "Unmatched POs": int((data["MATCH_STATUS"] != "FULLY MATCHED").sum()),
        "Pending Invoices": int((data["MATCH_STATUS"] == "INVOICE PENDING").sum()),
        "Total Unmatched Value": float(data.loc[data["UNMATCHED_VALUE"] > 0, "UNMATCHED_VALUE"].sum()),
    }


def vendor_summary(data: pd.DataFrame) -> pd.DataFrame:
    return data.groupby("VENDOR_NAME", as_index=False).agg(
        PO_VALUE=("PO_VALUE", "sum"),
        UNMATCHED_VALUE=("UNMATCHED_VALUE", lambda values: values.clip(lower=0).sum()),
        PO_COUNT=("PO_NUMBER", "nunique"),
    ).sort_values("PO_VALUE", ascending=False)


def material_summary(data: pd.DataFrame) -> pd.DataFrame:
    return data.groupby(["MATERIAL_ID", "MATERIAL_DESC"], as_index=False).agg(
        ORDER_QTY=("ORDER_QTY", "sum"),
        UNMATCHED_QTY=("UNMATCHED_QTY", lambda values: values.clip(lower=0).sum()),
        PO_VALUE=("PO_VALUE", "sum"),
    ).sort_values("PO_VALUE", ascending=False)


def data_quality(po: pd.DataFrame, receipts: pd.DataFrame) -> dict[str, object]:
    duplicate_po_lines = int(po.duplicated(["PO_NUMBER", "PO_ITEM"]).sum())
    duplicate_documents = int(receipts.duplicated(["DOCUMENT_ID"]).sum())
    missing_vendor = int(po[["VENDOR_ID", "VENDOR_NAME"]].isna().any(axis=1).sum())
    missing_price = int(po["UNIT_PRICE"].isna().sum())
    issues = missing_vendor + missing_price + duplicate_po_lines + duplicate_documents
    total = max(len(po) + len(receipts), 1)
    return {
        "PO Records": len(po),
        "Receipt Records": len(receipts),
        "Missing Vendor": missing_vendor,
        "Missing Price": missing_price,
        "Duplicate PO Lines": duplicate_po_lines,
        "Duplicate Documents": duplicate_documents,
        "Overall Quality": max(0.0, round((1 - issues / total) * 100, 1)),
    }
