"""Alerting facade used by the integration controller."""

from selective_surveillance.storage.event_store import EventStore


class AlertingService:
    """Apply event storage and local dashboard notification rules."""

    def __init__(
        self,
        database_path="data/events.sqlite3",
        image_dir="data/events",
        cooldown_seconds=60,
        retention_days=30,
    ) -> None:
        self._events = EventStore(
            database_path=database_path,
            image_dir=image_dir,
            cooldown_seconds=cooldown_seconds,
            retention_days=retention_days,
        )

    def record_event(self, **event_data):
        return self._events.record_event(**event_data)

    def update_event_identity(self, **event_data):
        return self._events.update_event_identity(**event_data)

    def list_events(self, limit=100):
        return self._events.list_events(limit)

    def latest_dashboard_alert(self):
        return self._events.latest_dashboard_alert()

    def purge_expired(self):
        return self._events.purge_expired()
