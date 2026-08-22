import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from nlp_parser import QueryIntent


SUPPORTED_OPERATIONS = {
    "lookup", "filter", "total_value", "count", "missing_invoice",
    "reconciliation", "explain", "top_vendor", "top_unmatched_vendor",
    "top_material", "top_material_qty",
}


def ai_is_configured() -> bool:
    return bool(os.getenv("AI_API_KEY"))


def translate_with_ai(question: str) -> QueryIntent | None:
    """Use an OpenAI-compatible API only to propose a structured intent.

    The returned object is still executed and verified by the local query engine.
    """
    api_key = os.getenv("AI_API_KEY")
    if not api_key:
        return None
    endpoint = os.getenv("AI_API_URL", "https://api.openai.com/v1/chat/completions")
    model = os.getenv("AI_MODEL", "gpt-4o-mini")
    payload = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Translate the question to JSON only. Never answer it. Allowed operation values: " + ", ".join(sorted(SUPPORTED_OPERATIONS)) + ". JSON keys: operation, po_number, vendor, threshold, document_type."},
            {"role": "user", "content": question},
        ],
    }
    request = Request(endpoint, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}, method="POST")
    try:
        with urlopen(request, timeout=8) as response:
            content = json.loads(response.read())
        raw = content["choices"][0]["message"]["content"]
        values = json.loads(raw)
        operation = values.get("operation")
        if operation not in SUPPORTED_OPERATIONS:
            return None
        threshold = values.get("threshold")
        return QueryIntent(operation=operation, po_number=_string_or_none(values.get("po_number")), vendor=_string_or_none(values.get("vendor")), threshold=float(threshold) if threshold is not None else None, document_type=_string_or_none(values.get("document_type")))
    except (HTTPError, URLError, TimeoutError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _string_or_none(value):
    return str(value) if value not in (None, "") else None
