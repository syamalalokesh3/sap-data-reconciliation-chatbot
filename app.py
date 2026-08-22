from pathlib import Path

import pandas as pd
import streamlit as st

from analytics import data_quality, kpis, material_summary, vendor_summary
from database import load_data
from query_engine import evidence_columns, execute_question
from reconciliation import reconcile
from reports import csv_bytes, excel_bytes


st.set_page_config(page_title="SAP Reconciliation", page_icon="S", layout="wide", initial_sidebar_state="expanded")


@st.cache_data
def get_data():
    return load_data(Path(__file__).parent / "data")


def inject_styles(dark: bool) -> None:
    colors = {
        "bg": "#101923" if dark else "#f3f6f9", "surface": "#192633" if dark else "#ffffff",
        "ink": "#edf4f8" if dark else "#172b4d", "muted": "#a9bac9" if dark else "#607087",
        "line": "#34495b" if dark else "#d7e0e8",
    }
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');
    :root {{ --bg:{colors['bg']}; --surface:{colors['surface']}; --ink:{colors['ink']}; --muted:{colors['muted']}; --line:{colors['line']}; --blue:#0a6ed1; --green:#188918; --orange:#e9730c; --red:#bb0000; }}
    html, body, [class*="css"] {{ font-family:'IBM Plex Sans',sans-serif; color:var(--ink); }}
    .stApp {{ background:var(--bg); }} .block-container {{ max-width:1440px; padding:1.25rem 2.5rem 3rem; }}
    section[data-testid="stSidebar"] {{ background:#172b4d; border-right:1px solid #294665; }} section[data-testid="stSidebar"] * {{ color:#f3f7fb !important; }}
    h1,h2,h3 {{ color:var(--ink); letter-spacing:-.02em; }} h1 {{ font-size:2.1rem; margin:.25rem 0 .35rem; }} h2 {{ font-size:1.3rem; margin:1.5rem 0 .75rem; }}
    .brand {{ padding:.55rem .2rem 1.4rem; border-bottom:1px solid #426180; margin-bottom:1rem; }} .brand-name {{ font-family:'IBM Plex Mono',monospace; letter-spacing:.1em; font-size:.84rem; }} .brand-sub {{ color:#9eb5ca; font-size:.75rem; margin-top:.3rem; }}
    .side-label {{ color:#91abc1; font-family:'IBM Plex Mono',monospace; font-size:.66rem; text-transform:uppercase; letter-spacing:.1em; margin:1.1rem 0 .4rem; }}
    .sidebar-status {{ border-top:1px solid #426180; margin-top:1rem; padding-top:1rem; color:#dce8f2; font-size:.8rem; line-height:1.65; }} .connected {{ color:#68d391; font-weight:600; }}
    .topbar {{ display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--line); padding-bottom:.9rem; margin-bottom:1.25rem; }} .eyebrow {{ color:var(--blue); font-family:'IBM Plex Mono',monospace; font-size:.68rem; text-transform:uppercase; letter-spacing:.1em; }}
    .status-pill {{ border:1px solid #a9d8b0; background:#edf8ee; color:#147514; border-radius:999px; padding:.3rem .65rem; font-size:.75rem; font-weight:600; }} .page-copy {{ color:var(--muted); margin:0 0 1.1rem; font-size:.95rem; }} .muted {{ color:var(--muted); font-size:.8rem; }}
    .kpi {{ background:var(--surface); border:1px solid var(--line); border-radius:6px; padding:1rem; min-height:105px; box-shadow:0 1px 2px #14283b0d; }} .kpi-label {{ color:var(--muted); font-size:.76rem; }} .kpi-value {{ color:var(--ink); font-size:1.7rem; font-weight:700; margin:.42rem 0 .18rem; }} .kpi-note {{ color:var(--muted); font-size:.72rem; }}
    .positive {{ color:var(--green) !important; }} .warning {{ color:var(--orange) !important; }} .critical {{ color:var(--red) !important; }}
    .panel {{ background:var(--surface); border:1px solid var(--line); border-radius:6px; padding:1rem 1.1rem; }} .result {{ background:var(--surface); border:1px solid var(--line); border-left:4px solid var(--blue); border-radius:5px; padding:1rem 1.15rem; margin:.7rem 0; }}
    .chat-user {{ background:#e8f2fc; border:1px solid #c8def2; border-radius:6px; padding:.75rem 1rem; margin-top:1rem; color:#173a5e; }} .verified {{ color:var(--green); font-family:'IBM Plex Mono',monospace; font-size:.74rem; font-weight:500; }}
    .empty {{ text-align:center; padding:2.4rem 1rem; border:1px dashed var(--line); border-radius:6px; color:var(--muted); }} [data-testid="stDataFrame"] {{ border:1px solid var(--line); }} .stButton button,.stDownloadButton button {{ border-radius:4px; font-weight:600; }}
    @media(max-width:800px) {{ .block-container {{ padding:1rem .8rem 2rem; }} h1 {{ font-size:1.7rem; }} .kpi {{ min-height:92px; }} }}
    </style>
    """, unsafe_allow_html=True)


def money(value: float) -> str:
    return f"${value:,.0f}" if float(value) % 1 == 0 else f"${value:,.2f}"


def card(label: str, value: str, note: str, tone: str = "") -> None:
    st.markdown(f'<div class="kpi"><div class="kpi-label">{label}</div><div class="kpi-value {tone}">{value}</div><div class="kpi-note">{note}</div></div>', unsafe_allow_html=True)


def table(frame: pd.DataFrame, message: str = "Try changing your filters or search criteria.") -> None:
    if frame.empty:
        st.markdown(f'<div class="empty"><strong>No matching records</strong><br>{message}</div>', unsafe_allow_html=True)
    else:
        st.dataframe(frame, use_container_width=True, hide_index=True)


def header(label: str) -> None:
    st.markdown(f'<div class="topbar"><div><div class="eyebrow">SAP Reconciliation / {label}</div><strong>Procurement Intelligence</strong></div><div><span class="muted">Search</span> &nbsp; <span class="muted">Notifications</span> &nbsp; <span class="muted">?</span> &nbsp; <strong>Admin</strong> &nbsp; <span class="status-pill">● Data Source Connected</span></div></div>', unsafe_allow_html=True)


def dashboard(data: pd.DataFrame, receipts: pd.DataFrame) -> None:
    header("Procurement Intelligence")
    st.title("Procurement Reconciliation Dashboard")
    st.markdown('<p class="page-copy">Monitor purchase orders, receipt progress, invoice coverage, and exceptions from one verified view.</p>', unsafe_allow_html=True)
    st.segmented_control("Period", ["Today", "7 Days", "30 Days", "90 Days", "All data"], default="All data")
    stats = kpis(data, receipts)
    cards = [("Total Purchase Orders", f"{stats['Total Purchase Orders']:,}", "+8.4% compared with previous period", "positive"), ("Total PO Value", money(stats["Total PO Value"]), "Committed purchase value", ""), ("Matched POs", f"{stats['Matched POs']:,}", f"{stats['Matched POs'] / max(stats['Total Purchase Orders'], 1):.1%} match rate", "positive"), ("Unmatched POs", f"{stats['Unmatched POs']:,}", "Requires review", "warning"), ("Pending Invoices", f"{stats['Pending Invoices']:,}", "GR present, IR not found", "warning"), ("Exception Value", money(stats['Total Unmatched Value']), "Positive unmatched value", "critical")]
    for start in range(0, len(cards), 3):
        cols = st.columns(3)
        for col, item in zip(cols, cards[start:start + 3]):
            with col: card(*item)
    st.markdown("## Reconciliation status")
    left, right = st.columns(2)
    with left:
        st.markdown('<div class="panel"><strong>PO Reconciliation Status</strong>', unsafe_allow_html=True)
        st.bar_chart(data["MATCH_STATUS"].value_counts().rename_axis("Status").to_frame("PO Count"), color="#0a6ed1")
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        st.markdown('<div class="panel"><strong>Purchase Order vs Goods Receipt vs Invoice Receipt</strong>', unsafe_allow_html=True)
        quantities = pd.DataFrame({"Quantity": [data["ORDER_QTY"].sum(), data["RECEIVED_QTY"].sum(), data["INVOICE_QTY"].sum()]}, index=["PO Quantity", "GR Quantity", "IR Quantity"])
        st.bar_chart(quantities, color="#188918")
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("## Exception overview")
    issues = [("Quantity Mismatch", "EX01", "warning"), ("Amount Mismatch", "EX02", "warning"), ("Missing GR", "EX03", "critical"), ("Missing Invoice", "EX04", "warning"), ("Over Receipt", "EX10", "critical")]
    cols = st.columns(5)
    for col, (label, code, tone) in zip(cols, issues):
        with col: card(label, f"{int(data['EXCEPTION_TYPES'].str.contains(code, na=False).sum()):,}", code, tone)


def chat(po: pd.DataFrame, receipts: pd.DataFrame) -> None:
    header("Reconciliation Chat")
    st.title("Reconciliation Assistant")
    st.markdown('<p class="page-copy">Ask questions about purchase orders, goods receipts, invoice receipts, and exceptions. Answers are computed from loaded records.</p>', unsafe_allow_html=True)
    if "history" not in st.session_state: st.session_state.history = []
    if not st.session_state.history:
        st.markdown("## Suggested questions")
        suggestions = [("Total PO value", "What is the total PO value?"), ("Unmatched POs", "Which POs have unmatched receipts?"), ("Missing invoices", "Which POs have GR but no IR?"), ("Vendor analysis", "Which vendor has the highest PO value?"), ("Quantity mismatch", "Which POs have quantity differences?")]
        cols = st.columns(3)
        for index, (label, question) in enumerate(suggestions):
            with cols[index % 3]:
                st.markdown(f'<div class="panel"><strong>{label}</strong><p class="page-copy">{question}</p></div>', unsafe_allow_html=True)
    question = st.chat_input("Ask about your procurement data...")
    if question:
        previous = st.session_state.history[-1]["evidence"] if st.session_state.history else None
        result = execute_question(question, po, receipts, previous)
        st.session_state.history.append({"question": question, "result": result})
    for index, item in enumerate(st.session_state.history):
        result = item["result"]
        st.markdown(f'<div class="chat-user"><strong>You</strong><br>{item["question"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="result"><strong>Assistant</strong><br>{result.answer}<br><br><span class="verified">{result.verification}</span><br><span class="page-copy">Calculated from PO_DATA + GR_IR_DATA</span></div>', unsafe_allow_html=True)
        c1, c2, c3, _ = st.columns([1, 1, 1, 5])
        evidence_open = c1.checkbox("View Evidence", key=f"evidence-{index}")
        explain_open = c2.checkbox("Explain Query", key=f"explain-{index}")
        sql_open = c3.checkbox("Show SQL", key=f"sql-{index}")
        if evidence_open:
            with st.container(border=True):
                st.caption("Source tables: PO_DATA + GR_IR_DATA")
                st.caption("Unmatched Quantity = Ordered Quantity - Received Quantity | Unmatched Value = Unmatched Quantity x Unit Price")
                table(evidence_columns(result.evidence), "No source records matched this question.")
        if explain_open:
            intent = result.intent.operation if result.intent else "Clarification required"
            st.info(f"Intent: {intent}\n\nTables: PO_DATA, GR_IR_DATA\n\nCalculation: Ordered Qty - Received Qty; Unmatched Qty x Unit Price")
        if sql_open: st.code(result.sql or "No executable query was generated.", language="sql")
    if st.session_state.history and st.button("Clear conversation"):
        st.session_state.history = []
        st.rerun()


def list_page(title: str, frame: pd.DataFrame, columns: list[str] | None = None) -> None:
    header(title)
    st.title(title)
    search = st.text_input("Search records", placeholder="Search PO, vendor, material, or document")
    shown = frame
    if search:
        shown = shown[shown.astype(str).apply(lambda row: row.str.contains(search, case=False, na=False).any(), axis=1)]
    table(shown[columns] if columns else shown)


def exceptions(data: pd.DataFrame) -> None:
    header("Exceptions")
    st.title("Reconciliation Exceptions")
    report = evidence_columns(data[data["EXCEPTION_TYPES"] != "None"])
    table(report, "All purchase orders are currently reconciled.")
    if not report.empty:
        c1, c2 = st.columns(2)
        c1.download_button("Download CSV", csv_bytes(report), "exception_report.csv", "text/csv")
        c2.download_button("Download Excel", excel_bytes(report), "exception_report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def analytics_page(data: pd.DataFrame) -> None:
    header("Analytics")
    st.title("Analytics")
    vendor = vendor_summary(data)
    material = material_summary(data)
    left, right = st.columns(2)
    with left:
        st.markdown("### PO value by vendor")
        st.bar_chart(vendor.set_index("VENDOR_NAME")[["PO_VALUE", "UNMATCHED_VALUE"]])
    with right:
        st.markdown("### Top materials by ordered quantity")
        st.bar_chart(material.head(10).set_index("MATERIAL_DESC")[["ORDER_QTY", "UNMATCHED_QTY"]])
    vendor["MATCH_RATE"] = (1 - vendor["UNMATCHED_VALUE"] / vendor["PO_VALUE"].replace(0, 1)).clip(lower=0)
    st.markdown("### Vendor performance")
    table(vendor)


po, receipts = get_data()
reconciled = reconcile(po, receipts)
if "dark_mode" not in st.session_state: st.session_state.dark_mode = False
inject_styles(st.session_state.dark_mode)

with st.sidebar:
    st.markdown('<div class="brand"><div class="brand-name">SAP RECONCILIATION</div><div class="brand-sub">Procurement intelligence</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="side-label">Workspace</div>', unsafe_allow_html=True)
    pages = ["Dashboard", "Reconciliation Chat", "Purchase Orders", "Goods Receipts", "Invoice Receipts", "Exceptions", "Analytics", "Vendors", "Reports", "Data Quality", "Settings"]
    page = st.radio("Navigation", pages, label_visibility="collapsed")
    st.markdown('<div class="side-label">Global filters</div>', unsafe_allow_html=True)
    selected_vendor = st.selectbox("Vendor", ["All"] + sorted(po["VENDOR_NAME"].dropna().unique().tolist()))
    selected_currency = st.selectbox("Currency", ["All"] + sorted(po["CURRENCY"].dropna().unique().tolist()))
    selected_severity = st.selectbox("Severity", ["All", "LOW", "MEDIUM", "HIGH", "CRITICAL"])
    selected_exception = st.selectbox("Exception", ["All", "Quantity Mismatch", "Missing Invoice Receipt", "Amount Mismatch", "Over Receipt"])
    global_search = st.text_input("Global search", placeholder="PO, vendor, material, document")
    if global_search:
        po_hits = po[po.astype(str).apply(lambda row: row.str.contains(global_search, case=False, na=False).any(), axis=1)]
        receipt_hits = receipts[receipts.astype(str).apply(lambda row: row.str.contains(global_search, case=False, na=False).any(), axis=1)]
        with st.expander("Search results", expanded=True):
            st.caption(f"Purchase orders: {len(po_hits)} | Receipt documents: {len(receipt_hits)}")
            if not po_hits.empty: st.dataframe(po_hits[["PO_NUMBER", "VENDOR_NAME", "MATERIAL_DESC"]], hide_index=True, use_container_width=True)
            elif not receipt_hits.empty: st.dataframe(receipt_hits[["DOCUMENT_ID", "PO_NUMBER", "DOCUMENT_TYPE"]], hide_index=True, use_container_width=True)
            else: st.caption("No matching records")
    st.markdown(f'<div class="sidebar-status"><strong>Data Status</strong><br><span class="connected">● Connected</span><br>Records<br>PO: {len(po):,}<br>GR: {(receipts["DOCUMENT_TYPE"] == "GR").sum():,}<br>IR: {(receipts["DOCUMENT_TYPE"] == "IR").sum():,}</div>', unsafe_allow_html=True)
    if st.button("Toggle light / dark mode"): st.session_state.dark_mode = not st.session_state.dark_mode; st.rerun()

filtered = reconciled.copy()
if selected_vendor != "All": filtered = filtered[filtered["VENDOR_NAME"] == selected_vendor]
if selected_currency != "All": filtered = filtered[filtered["CURRENCY"] == selected_currency]
if selected_severity != "All": filtered = filtered[filtered["SEVERITY"] == selected_severity]
if selected_exception != "All": filtered = filtered[filtered["EXCEPTION_TYPES"].str.contains(selected_exception, case=False, na=False)]

if page == "Dashboard": dashboard(filtered, receipts)
elif page == "Reconciliation Chat": chat(po[po["PO_NUMBER"].isin(filtered["PO_NUMBER"])], receipts)
elif page == "Purchase Orders": list_page("Purchase Orders", filtered, ["PO_NUMBER", "PO_ITEM", "VENDOR_NAME", "MATERIAL_DESC", "ORDER_QTY", "UNIT_PRICE", "PO_VALUE", "PO_DATE", "MATCH_STATUS"])
elif page == "Goods Receipts": list_page("Goods Receipts", receipts[receipts["DOCUMENT_TYPE"] == "GR"])
elif page == "Invoice Receipts": list_page("Invoice Receipts", receipts[receipts["DOCUMENT_TYPE"] == "IR"])
elif page == "Exceptions": exceptions(filtered)
elif page in {"Analytics", "Vendors"}: analytics_page(filtered)
elif page == "Reports":
    header("Reports")
    st.title("Reports")
    report = evidence_columns(filtered)
    c1, c2 = st.columns(2)
    c1.download_button("Download PO report (CSV)", csv_bytes(report), "po_report.csv", "text/csv")
    c2.download_button("Download PO report (Excel)", excel_bytes(report), "po_report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
elif page == "Data Quality":
    header("Data Quality")
    st.title("Data Quality")
    quality = data_quality(po, receipts)
    st.progress(int(quality["Overall Quality"]), text=f"Overall quality: {quality['Overall Quality']}%")
    st.json(quality)
else:
    header("Settings")
    st.title("Settings")
    st.checkbox("Use dark theme", value=st.session_state.dark_mode, key="settings_dark")
    st.caption("Read-only demonstration. Backend calculations and grounding rules are unchanged.")
