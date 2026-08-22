from pathlib import Path

from database import load_data
from query_engine import execute_question
from analytics import data_quality, kpis
from reconciliation import reconcile
from reports import csv_bytes, excel_bytes


PO, RECEIPTS = load_data(Path(__file__).parents[1] / "data")


def test_lookup():
    result = execute_question("Show PO 4500001001.", PO, RECEIPTS)
    assert "ABC Supplies" in result.answer
    assert len(result.evidence) == 1


def test_vendor_filter_and_total():
    filtered = execute_question("Show all POs for vendor ABC Supplies", PO, RECEIPTS)
    assert set(filtered.evidence["PO_NUMBER"]) == {"4500001001", "4500001004"}
    total = execute_question("What is the total PO value for vendor XYZ Metals?", PO, RECEIPTS)
    assert "$8,000" in total.answer


def test_reconciliation_threshold():
    result = execute_question("Which POs have unmatched receipts over $1,000?", PO, RECEIPTS)
    assert set(result.evidence["PO_NUMBER"]) == {"4500001002", "4500001005"}


def test_missing_invoice_and_explanation():
    missing = execute_question("Which POs have goods receipts but no invoice receipt?", PO, RECEIPTS)
    assert set(missing.evidence["PO_NUMBER"]) == {"4500001003", "4500001005"}
    explanation = execute_question("Why is PO 4500001002 unmatched?", PO, RECEIPTS)
    assert "50 units remain unmatched" in explanation.answer
    assert "$2,000" in explanation.answer


def test_unknown_and_ambiguous_queries_are_safe():
    unknown = execute_question("Show PO 9999999999.", PO, RECEIPTS)
    assert "not found" in unknown.answer
    ambiguous = execute_question("Show high-value POs.", PO, RECEIPTS)
    assert "threshold" in ambiguous.answer


def test_three_way_match_statuses_and_exceptions():
    data = reconcile(PO, RECEIPTS).set_index("PO_NUMBER")
    assert data.loc["4500001001", "MATCH_STATUS"] == "FULLY MATCHED"
    assert data.loc["4500001002", "MATCH_STATUS"] == "PARTIAL RECEIPT"
    assert "EX04 Missing Invoice Receipt" in data.loc["4500001003", "EXCEPTION_TYPES"]
    assert data.loc["4500001002", "SEVERITY"] == "HIGH"


def test_quality_kpis_analytics_exports_and_follow_up():
    data = reconcile(PO, RECEIPTS)
    dashboard = kpis(data, RECEIPTS)
    assert dashboard["Total Purchase Orders"] == 5
    assert dashboard["Pending Invoices"] == 2
    assert data_quality(PO, RECEIPTS)["Overall Quality"] == 100.0
    first = execute_question("Which POs have unmatched receipts?", PO, RECEIPTS)
    follow_up = execute_question("Show only those above $1,000.", PO, RECEIPTS, first.evidence)
    assert set(follow_up.evidence["PO_NUMBER"]) == {"4500001002", "4500001005"}
    assert csv_bytes(data).startswith(b"PO_NUMBER")
    assert excel_bytes(data)
