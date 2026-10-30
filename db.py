import sqlite3
from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    image_filename TEXT NOT NULL,
    predicted_class TEXT NOT NULL,
    confidence REAL NOT NULL,
    advice TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    plant_name TEXT NOT NULL DEFAULT 'My plant',
    green REAL NOT NULL DEFAULT 0,
    yellow REAL NOT NULL DEFAULT 0,
    brown REAL NOT NULL DEFAULT 0,
    health INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
"""

NEW_COLS = {"plant_name": "TEXT NOT NULL DEFAULT 'My plant'", "green": "REAL NOT NULL DEFAULT 0",
            "yellow": "REAL NOT NULL DEFAULT 0", "brown": "REAL NOT NULL DEFAULT 0", "health": "INTEGER NOT NULL DEFAULT 0"}

def migrate(db):
    have = {r[1] for r in db.execute("PRAGMA table_info(predictions)")}
    for col, typ in NEW_COLS.items():
        if col not in have:
            db.execute(f"ALTER TABLE predictions ADD COLUMN {col} {typ}")

def get_db():
    if "db" not in g:
        db_path = current_app.config.get("DATABASE", current_app.instance_path + "/plantcare.db")
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_app(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        db = get_db()
        db.executescript(SCHEMA)
        migrate(db)
        db.commit()
