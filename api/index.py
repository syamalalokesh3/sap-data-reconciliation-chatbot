import json
from pathlib import Path
from http.server import BaseHTTPRequestHandler

from database import load_data
from query_engine import evidence_columns, execute_question


ROOT = Path(__file__).resolve().parents[1]
PO, RECEIPTS = load_data(ROOT / "data")


class handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self._send(204, {})

    def do_GET(self) -> None:
        self._send(200, {
            "service": "SAP Data Reconciliation API",
            "status": "connected",
            "records": {"po": len(PO), "gr_ir": len(RECEIPTS)},
            "usage": "POST {\"question\": \"Which POs have unmatched receipts over $1,000?\"}",
        })

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(length) or b"{}")
            question = request.get("question", "")
            if not isinstance(question, str) or not question.strip():
                self._send(400, {"error": "question must be a non-empty string"})
                return
            result = execute_question(question, PO, RECEIPTS)
            evidence = evidence_columns(result.evidence).to_dict(orient="records")
            self._send(200, {
                "answer": result.answer,
                "verification": result.verification,
                "intent": result.intent.operation if result.intent else None,
                "sql": result.sql,
                "evidence": evidence,
            })
        except (json.JSONDecodeError, TypeError, ValueError) as error:
            self._send(400, {"error": f"Invalid request: {error}"})
        except Exception as error:
            self._send(500, {"error": "Unable to process the question", "detail": str(error)})
