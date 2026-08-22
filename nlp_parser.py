from dataclasses import dataclass
import re


@dataclass(frozen=True)
class QueryIntent:
    operation: str
    po_number: str | None = None
    vendor: str | None = None
    threshold: float | None = None
    document_type: str | None = None
    date_start: str | None = None
    date_end: str | None = None


def parse_question(question: str) -> QueryIntent | str:
    text = question.strip()
    lower = text.lower()
    po_match = re.search(r"\b(\d{10})\b", text)
    po_number = po_match.group(1) if po_match else None
    money = re.search(r"(?:\$|usd\s*)([\d,]+(?:\.\d+)?)", lower)
    threshold = float(money.group(1).replace(",", "")) if money else None

    if "high-value" in lower or "high value" in lower:
        return "What value should be considered high-value? Please provide a threshold, such as $10,000."
    if "those" in lower and threshold is not None:
        return QueryIntent("reconciliation", threshold=threshold)
    if lower in {"show my pos", "show my po", "show receipts", "show receipt"}:
        return "Please specify a vendor, PO number, date range, or whether you want GR, IR, or both."
    if "receipt" in lower and not any(word in lower for word in ("unmatched", "received", "invoice", "goods")):
        return "Do you want Goods Receipts, Invoice Receipts, or both?"
    if "no invoice" in lower or "missing invoice" in lower or "without invoice" in lower:
        return QueryIntent("missing_invoice")
    if "why" in lower and po_number:
        return QueryIntent("explain", po_number=po_number)
    if "highest po value" in lower and "vendor" in lower:
        return QueryIntent("top_vendor")
    if "highest unmatched" in lower and "vendor" in lower:
        return QueryIntent("top_unmatched_vendor")
    if "highest" in lower and "material" in lower:
        return QueryIntent("top_material_qty" if "quantity" in lower else "top_material")
    if "unmatched" in lower or "received less" in lower or "does not match" in lower:
        return QueryIntent("reconciliation", threshold=threshold)
    if "total" in lower and "value" in lower:
        return QueryIntent("total_value", vendor=_extract_vendor(text))
    if "how many" in lower and "po" in lower:
        return QueryIntent("count", vendor=_extract_vendor(text))
    if po_number:
        return QueryIntent("lookup", po_number=po_number)
    if "po" in lower and ("vendor" in lower or _extract_vendor(text)):
        return QueryIntent("filter", vendor=_extract_vendor(text))
    return "I can currently answer questions about POs, goods receipts, invoice receipts, quantities, values, vendors, and reconciliation."


def _extract_vendor(text: str) -> str | None:
    match = re.search(r"(?:vendor\s+(?:is\s+)?|from\s+)([A-Za-z][A-Za-z ]+?)(?:\?|\.|$)", text, re.IGNORECASE)
    return match.group(1).strip() if match else None
