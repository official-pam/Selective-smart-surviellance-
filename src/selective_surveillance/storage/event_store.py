import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone

from selective_surveillance.alerting.policy import should_raise_dashboard_alert
from selective_surveillance.storage.exceptions import StorageError

def current_time():
    return datetime.now(timezone.utc)


def parse_time(value):
    if not value:
        return current_time()

    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


class EventStore:
    def __init__(self, database_path='data/events.sqlite3', image_dir='data/events',
                 cooldown_seconds=60, retention_days=30):
        self.database_path = database_path
        self.image_dir = image_dir
        self.cooldown_seconds = max(0, int(cooldown_seconds))
        self.retention_days = max(1, int(retention_days))

        database_directory = os.path.dirname(database_path)
        if database_directory:
            os.makedirs(database_directory, mode=0o700, exist_ok=True)
        os.makedirs(image_dir, mode=0o700, exist_ok=True)

        self._initialize()
        self._set_permissions(database_path, 0o600)
        self.purge_expired()

    def _connect(self):
        db = sqlite3.connect(self.database_path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def _initialize(self):
        db = self._connect()

        try:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    occurred_at TEXT NOT NULL,
                    track_id TEXT,
                    zone TEXT NOT NULL,
                    recognition TEXT NOT NULL,
                    similarity REAL,
                    face_status TEXT NOT NULL,
                    face_image_path TEXT,
                    full_frame_path TEXT,
                    alert_status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_events_occurred_at
                    ON events(occurred_at DESC);
                CREATE INDEX IF NOT EXISTS idx_events_alert_status
                    ON events(alert_status, occurred_at DESC);
                CREATE TABLE IF NOT EXISTS cooldowns (
                    zone TEXT NOT NULL,
                    track_id TEXT NOT NULL,
                    last_alert_at TEXT NOT NULL,
                    PRIMARY KEY(zone, track_id)
                );
            ''')

            columns = {
                row['name']
                for row in db.execute('PRAGMA table_info(events)').fetchall()
            }
            if 'confidence' in columns and 'similarity' not in columns:
                db.execute(
                    'ALTER TABLE events RENAME COLUMN confidence TO similarity'
                )

            db.commit()
        except sqlite3.Error as e:
            db.rollback()
            raise StorageError(f'could not initialize alert storage: {e}')
        finally:
            db.close()

    def record_event(self, known, similarity, zone, track_id=None, occurred_at=None,
                     face_status='captured', face_image=None, full_frame=None):
        event_id = str(uuid.uuid4())
        event_time = parse_time(occurred_at)
        occurred_at = event_time.isoformat(timespec='seconds')
        created_at = current_time().isoformat(timespec='seconds')
        recognition = {True: 'known', False: 'unknown'}.get(known, 'inconclusive')

        face_path = None
        frame_path = None

        try:
            face_path = self._save_image(event_id, 'face', face_image)
            frame_path = self._save_image(event_id, 'frame', full_frame)
        except StorageError:
            self._remove_image(face_path)
            self._remove_image(frame_path)
            raise

        db = self._connect()

        try:
            alert_status = 'not_applicable'

            if should_raise_dashboard_alert(known):
                alert_status = self._claim_alert(db, zone, track_id, event_time)

            db.execute('''
                INSERT INTO events
                (id, occurred_at, track_id, zone, recognition, similarity,
                 face_status, face_image_path, full_frame_path, alert_status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event_id, occurred_at, track_id, zone, recognition, similarity,
                face_status, face_path, frame_path, alert_status, created_at,
            ))
            db.commit()
        except sqlite3.Error as e:
            db.rollback()
            self._remove_image(face_path)
            self._remove_image(frame_path)
            raise StorageError(f'could not save event: {e}')
        finally:
            db.close()

        return {
            'event_id': event_id,
            'alert_status': alert_status,
            'face_image_path': face_path,
            'full_frame_path': frame_path,
        }

    def _claim_alert(self, db, zone, track_id, event_time):
        if track_id is None:
            return 'dashboard_alert'

        row = db.execute(
            'SELECT last_alert_at FROM cooldowns WHERE zone = ? AND track_id = ?',
            (zone, str(track_id)),
        ).fetchone()

        if row and event_time - parse_time(row['last_alert_at']) < timedelta(seconds=self.cooldown_seconds):
            return 'cooldown'

        db.execute('''
            INSERT INTO cooldowns(zone, track_id, last_alert_at)
            VALUES (?, ?, ?)
            ON CONFLICT(zone, track_id)
            DO UPDATE SET last_alert_at = excluded.last_alert_at
        ''', (zone, str(track_id), event_time.isoformat(timespec='seconds')))

        return 'dashboard_alert'

    def _save_image(self, event_id, image_type, image):
        if not image:
            return None

        image_path = os.path.join(self.image_dir, f'{event_id}-{image_type}.jpg')

        try:
            f = open(image_path, 'wb')
            f.write(image)
            f.close()
        except OSError as e:
            self._remove_image(image_path)
            raise StorageError(f'could not save image to {image_path}: {e}')

        self._set_permissions(image_path, 0o600)
        return image_path

    def _remove_image(self, image_path):
        if image_path:
            try:
                os.remove(image_path)
            except OSError:
                pass

    def _set_permissions(self, path, permissions):
        try:
            os.chmod(path, permissions)
        except OSError:
            pass

    def list_events(self, limit=100):
        db = self._connect()

        try:
            rows = db.execute(
                'SELECT * FROM events ORDER BY occurred_at DESC LIMIT ?',
                (max(1, min(int(limit), 500)),),
            ).fetchall()
        except sqlite3.Error as e:
            raise StorageError(f'could not read events: {e}')
        finally:
            db.close()

        return [dict(row) for row in rows]

    def latest_dashboard_alert(self):
        db = self._connect()

        try:
            row = db.execute(
                "SELECT * FROM events WHERE alert_status = 'dashboard_alert' "
                'ORDER BY occurred_at DESC LIMIT 1'
            ).fetchone()
        except sqlite3.Error as e:
            raise StorageError(f'could not read latest dashboard alert: {e}')
        finally:
            db.close()

        return dict(row) if row else None

    def purge_expired(self):
        cutoff = (current_time() - timedelta(days=self.retention_days)).isoformat(timespec='seconds')
        db = self._connect()

        try:
            expired = db.execute(
                'SELECT face_image_path, full_frame_path FROM events WHERE occurred_at < ?',
                (cutoff,),
            ).fetchall()
            db.execute('DELETE FROM events WHERE occurred_at < ?', (cutoff,))
            db.execute('DELETE FROM cooldowns WHERE last_alert_at < ?', (cutoff,))
            db.commit()
        except sqlite3.Error as e:
            db.rollback()
            raise StorageError(f'could not remove expired events: {e}')
        finally:
            db.close()

        for event in expired:
            self._remove_image(event['face_image_path'])
            self._remove_image(event['full_frame_path'])

        return len(expired)


