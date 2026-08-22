# SAP-Style Data Reconciliation Chatbot

A deterministic Streamlit demo for asking grounded questions about mock purchase orders, goods receipts, and invoice receipts. It uses Pandas and never invents records or numerical answers.

## Run

```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```

The Vercel frontend uses Next.js and React. Install Node.js 20+ locally, then run:

```powershell
npm install
npm run dev
```

The Next.js dashboard is served at `http://localhost:3000` and calls the existing `/api` function in deployment. The Python Streamlit dashboard remains available through `app.py`.

## Test

```powershell
python -m pytest -q
```

## Deploy

The complete dashboard is a Streamlit application and can be deployed with Streamlit Community Cloud using `app.py`. This repository also includes a Vercel-compatible browser frontend at `/` and read-only API:

```text
GET  /api
POST /api   {"question": "Which POs have unmatched receipts over $1,000?"}
```

Vercel serves `index.html` at the root and routes `/api` to the Python function. The Streamlit app remains available for the full native dashboard experience on Streamlit Community Cloud.

## Query pipeline

```text
Rule-based NLP -> optional AI intent translation -> QueryIntent validation
-> read-only SQL validation -> local Pandas/database execution -> grounded answer
```

Rule-based parsing is always attempted first. To enable the optional OpenAI-compatible translation fallback, configure `AI_API_KEY` and optionally `AI_API_URL` and `AI_MODEL`. The AI service proposes an intent only; it cannot execute SQL or generate the final answer. `sql_validator.py` permits only one `SELECT`/`WITH` statement against `PO_DATA` and `GR_IR_DATA` and blocks destructive operations.

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
