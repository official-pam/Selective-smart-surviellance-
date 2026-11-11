"""Local rules for deciding when the dashboard should raise an alert."""


def should_raise_dashboard_alert(known: bool | None) -> bool:
    """Alert when entry occurs before a person is confirmed as registered.

    ``None`` means the face is not yet clear or could not be detected. The
    event is still a potential intruder entry until recognition confirms it.
    """
    return known is not True
