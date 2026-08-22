from pathlib import Path

import pandas as pd


PO_COLUMNS = {
    "PO_NUMBER", "PO_ITEM", "VENDOR_ID", "VENDOR_NAME", "MATERIAL_ID",
    "MATERIAL_DESC", "ORDER_QTY", "UNIT_PRICE", "PO_VALUE", "PO_DATE", "CURRENCY",
}
GR_IR_COLUMNS = {
    "DOCUMENT_ID", "PO_NUMBER", "PO_ITEM", "DOCUMENT_TYPE", "DOCUMENT_DATE",
    "RECEIVED_QTY", "INVOICE_QTY", "AMOUNT", "CURRENCY",
}


def load_data(data_dir: str | Path = "data") -> tuple[pd.DataFrame, pd.DataFrame]:
    data_path = Path(data_dir)
    po = pd.read_csv(data_path / "po_data.csv", dtype={"PO_NUMBER": str, "PO_ITEM": int})
    receipts = pd.read_csv(data_path / "gr_ir_data.csv", dtype={"PO_NUMBER": str, "PO_ITEM": int})
    validate_data(po, receipts)
    return po, receipts


def validate_data(po: pd.DataFrame, receipts: pd.DataFrame) -> None:
    missing_po = PO_COLUMNS - set(po.columns)
    missing_receipts = GR_IR_COLUMNS - set(receipts.columns)
    if missing_po or missing_receipts:
        raise ValueError(f"Missing columns: PO={sorted(missing_po)}, GR_IR={sorted(missing_receipts)}")
    if po["PO_NUMBER"].isna().any() or ~po["PO_NUMBER"].astype(str).str.fullmatch(r"\d{10}").all():
        raise ValueError("PO_NUMBER values must be 10-digit numbers")
    for column in ("ORDER_QTY", "UNIT_PRICE", "PO_VALUE"):
        if not pd.api.types.is_numeric_dtype(po[column]):
            raise ValueError(f"{column} must be numeric")
    for column in ("RECEIVED_QTY", "INVOICE_QTY", "AMOUNT"):
        if not pd.api.types.is_numeric_dtype(receipts[column]):
            raise ValueError(f"{column} must be numeric")
    invalid_types = set(receipts["DOCUMENT_TYPE"].dropna()) - {"GR", "IR"}
    if invalid_types:
        raise ValueError(f"Invalid document types: {sorted(invalid_types)}")
