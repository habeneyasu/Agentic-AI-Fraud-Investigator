"""ISO country codes for deterministic demo / corridor risk tiers (UI + triage + intake)."""

HIGH_RISK_COUNTRIES = frozenset({"IR", "KP", "SY", "CU", "VE", "MM", "BY"})
MEDIUM_RISK_COUNTRIES = frozenset({"RU", "UA", "PK", "BD", "GH", "KE", "TZ", "CN", "AF"})


def corridor_severity(country: str, amount: float) -> str:
    """Map destination country + amount to a coarse ``critical`` / ``high`` / ``medium`` tier."""
    c = (country or "").strip().upper()
    try:
        amt = float(amount or 0.0)
    except (TypeError, ValueError):
        amt = 0.0
    if c in HIGH_RISK_COUNTRIES or amt > 50_000:
        return "critical"
    if c in MEDIUM_RISK_COUNTRIES or amt > 10_000:
        return "high"
    return "medium"
