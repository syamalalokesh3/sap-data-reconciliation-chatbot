import re


ALLOWED_TABLES = {"PO_DATA", "GR_IR_DATA"}
BLOCKED_KEYWORDS = {"DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "REPLACE", "ATTACH", "DETACH"}


def validate_read_only_sql(sql: str) -> str:
    """Return SQL only when it is a single, approved read-only statement."""
    normalized = sql.strip()
    if not normalized:
        raise ValueError("SQL query cannot be empty")
    statements = [part.strip() for part in normalized.split(";") if part.strip()]
    if len(statements) != 1:
        raise ValueError("Only one SQL statement is allowed")
    statement = statements[0]
    first_word = statement.split(None, 1)[0].upper()
    if first_word not in {"SELECT", "WITH"}:
        raise ValueError("Only SELECT or WITH queries are allowed")
    upper = statement.upper()
    blocked = sorted(keyword for keyword in BLOCKED_KEYWORDS if re.search(rf"\b{keyword}\b", upper))
    if blocked:
        raise ValueError(f"Blocked SQL operation: {', '.join(blocked)}")
    tables = set(re.findall(r"\b(?:FROM|JOIN)\s+([A-Z_][A-Z0-9_]*)", upper))
    unknown_tables = tables - ALLOWED_TABLES
    if unknown_tables:
        raise ValueError(f"Unapproved table: {', '.join(sorted(unknown_tables))}")
    return statement
