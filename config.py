SEVERITY_THRESHOLDS = {
    "LOW": 500.0,
    "MEDIUM": 2000.0,
    "HIGH": 10000.0,
}


def severity_for(value: float) -> str:
    amount = abs(float(value))
    if amount < SEVERITY_THRESHOLDS["LOW"]:
        return "LOW"
    if amount < SEVERITY_THRESHOLDS["MEDIUM"]:
        return "MEDIUM"
    if amount < SEVERITY_THRESHOLDS["HIGH"]:
        return "HIGH"
    return "CRITICAL"
