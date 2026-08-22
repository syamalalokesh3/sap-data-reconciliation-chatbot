# SAP-Style Data Reconciliation Chatbot

A deterministic Streamlit demo for asking grounded questions about mock purchase orders, goods receipts, and invoice receipts. It uses Pandas and never invents records or numerical answers.

## Run

```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```

## Test

```powershell
python -m pytest -q
```

## Deploy

The complete dashboard is a Streamlit application and can be deployed with Streamlit Community Cloud using `app.py`. Vercel does not host Streamlit processes, so this repository also includes a Vercel-compatible read-only API:

```text
GET  /api
POST /api   {"question": "Which POs have unmatched receipts over $1,000?"}
```

Connect the Vercel API to a separate frontend, or use Streamlit Community Cloud for the full dashboard experience.

## Structure

- `app.py`: Streamlit chat interface
- `database.py`: CSV loading and validation
- `nlp_parser.py`: deterministic natural-language intent parser
- `query_engine.py`: query execution and grounded response formatting
- `reconciliation.py`: PO, GR, and IR calculations
- `analytics.py`: KPIs, vendor/material summaries, and data quality scoring
- `config.py`: configurable exception severity thresholds
- `reports.py`: CSV and Excel report exports
- `data/`: mock SAP-style source tables
- `tests/`: required behavior checks

The application supports PO lookup, vendor filtering, total and count aggregates, receipt mismatch thresholds, three-way matching, exception codes and severity, missing invoices, vendor/material analytics, dashboard charts, configurable sidebar filters, query explanations, SQL previews, evidence panels, CSV/Excel exports, session chat history, conversational follow-ups, and safe handling of unknown or ambiguous questions. All numerical answers are computed from the loaded PO and GR/IR records.
