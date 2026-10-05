import json
import os
import sqlite3
from pathlib import Path


DEFAULT_DB_PATH = Path(__file__).parent / "instance" / "fundraiser.sqlite3"


def _connection():
    db_path = Path(os.environ.get("DATABASE_PATH", DEFAULT_DB_PATH))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.execute("CREATE TABLE IF NOT EXISTS app_state (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    return connection


def load_state(default_state):
    connection = _connection()
    rows = dict(connection.execute("SELECT key, value FROM app_state"))
    if not rows:
        save_state(default_state, connection)
        rows = {key: json.dumps(value) for key, value in default_state.items()}
    connection.close()
    return {key: json.loads(value) for key, value in rows.items()}


def save_state(state, connection=None):
    owns_connection = connection is None
    connection = connection or _connection()
    connection.executemany(
        "INSERT INTO app_state(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        [(key, json.dumps(value)) for key, value in state.items()],
    )
    connection.commit()
    if owns_connection:
        connection.close()
