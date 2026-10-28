"""
Database Module — SQLite logging for all detection events
No external database server needed — SQLite is built into Python
Tables:
  - events      → every alert that was fired
  - detections  → every person detected (even under 30s)
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from loguru import logger


DB_PATH = "security.db"


def get_connection() -> sqlite3.Connection:
    """Get SQLite connection with row factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """
    Create all tables if they don't exist.
    Call once on startup.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Events table — every 30s alert
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT    NOT NULL,
            track_id    INTEGER NOT NULL,
            name        TEXT    DEFAULT 'UNKNOWN',
            is_known    INTEGER DEFAULT 0,
            confidence  REAL    DEFAULT 0.0,
            duration    REAL    DEFAULT 30.0,
            image_path  TEXT,
            alert_sent  INTEGER DEFAULT 1
        )
    """)

    # Detections table — every person seen (including under 30s)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detections (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT    NOT NULL,
            track_id    INTEGER NOT NULL,
            name        TEXT    DEFAULT 'UNKNOWN',
            is_known    INTEGER DEFAULT 0,
            confidence  REAL    DEFAULT 0.0,
            duration    REAL    DEFAULT 0.0,
            alerted     INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()
    logger.success("Database initialized — security.db ready.")


def log_event(track_id: int, name: str, is_known: bool,
              confidence: float, duration: float,
              image_path: str = None, alert_sent: bool = True):
    """
    Log a 30s alert event to the events table.
    Called every time an alert fires.
    """
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO events
            (timestamp, track_id, name, is_known, confidence,
             duration, image_path, alert_sent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            track_id,
            name,
            int(is_known),
            confidence,
            duration,
            image_path,
            int(alert_sent)
        ))
        conn.commit()
        logger.success(f"Event logged — ID:{track_id} | {name}")
    except Exception as e:
        logger.error(f"Failed to log event: {e}")
    finally:
        conn.close()


def log_detection(track_id: int, name: str, is_known: bool,
                  confidence: float, duration: float,
                  alerted: bool = False):
    """
    Log every detection (including people who left before 30s).
    Called when a track ID is cleaned up from timer manager.
    """
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO detections
            (timestamp, track_id, name, is_known,
             confidence, duration, alerted)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            track_id,
            name,
            int(is_known),
            confidence,
            duration,
            int(alerted)
        ))
        conn.commit()
        logger.debug(f"Detection logged — ID:{track_id} | {name} | {duration:.1f}s")
    except Exception as e:
        logger.error(f"Failed to log detection: {e}")
    finally:
        conn.close()


def get_recent_events(limit: int = 50) -> list[dict]:
    """Fetch most recent alert events — used by dashboard."""
    conn = get_connection()
    try:
        cursor = conn.execute("""
            SELECT * FROM events
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        rows = [dict(row) for row in cursor.fetchall()]
        return rows
    except Exception as e:
        logger.error(f"Failed to fetch events: {e}")
        return []
    finally:
        conn.close()


def get_stats() -> dict:
    """
    Get summary statistics for dashboard.
    Returns counts of total/known/unknown alerts.
    """
    conn = get_connection()
    try:
        stats = {}

        # Total alerts
        stats["total_alerts"] = conn.execute(
            "SELECT COUNT(*) FROM events"
        ).fetchone()[0]

        # Known person alerts
        stats["known_alerts"] = conn.execute(
            "SELECT COUNT(*) FROM events WHERE is_known = 1"
        ).fetchone()[0]

        # Unknown alerts
        stats["unknown_alerts"] = conn.execute(
            "SELECT COUNT(*) FROM events WHERE is_known = 0"
        ).fetchone()[0]

        # Total detections
        stats["total_detections"] = conn.execute(
            "SELECT COUNT(*) FROM detections"
        ).fetchone()[0]

        # Today's alerts
        today = datetime.now().strftime("%Y-%m-%d")
        stats["today_alerts"] = conn.execute(
            "SELECT COUNT(*) FROM events WHERE timestamp LIKE ?",
            (f"{today}%",)
        ).fetchone()[0]

        # Most seen person
        row = conn.execute("""
            SELECT name, COUNT(*) as count
            FROM events
            WHERE is_known = 1
            GROUP BY name
            ORDER BY count DESC
            LIMIT 1
        """).fetchone()
        stats["most_seen"] = dict(row) if row else {"name": "N/A", "count": 0}

        return stats

    except Exception as e:
        logger.error(f"Failed to fetch stats: {e}")
        return {}
    finally:
        conn.close()


def get_hourly_activity() -> list[dict]:
    """Get alert counts per hour — used for chart in dashboard."""
    conn = get_connection()
    try:
        cursor = conn.execute("""
            SELECT
                strftime('%H:00', timestamp) as hour,
                COUNT(*) as count
            FROM events
            GROUP BY hour
            ORDER BY hour
        """)
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Failed to fetch hourly activity: {e}")
        return []
    finally:
        conn.close()