"""Local rules for deciding when the dashboard should raise an alert."""


def should_raise_dashboard_alert(known: bool | None) -> bool:
    """Alert only on a definite no-match; unclear results need human review."""
    return known is False
