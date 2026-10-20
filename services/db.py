import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "wastewise.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  identifier TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'student' CHECK (role IN ('student','admin')),
  hostel_or_dept TEXT,
  total_points INTEGER NOT NULL DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS bins (
  bin_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  lat REAL NOT NULL,
  lng REAL NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('wet','dry','recyclable','ewaste','hazardous')),
  size TEXT NOT NULL CHECK (size IN ('small','medium','large','bulk')),
  capacity_litres INTEGER NOT NULL,
  usage TEXT NOT NULL CHECK (usage IN ('low','medium','high','very high')),
  fill_pct REAL NOT NULL DEFAULT 0,
  fill_rate_per_hr REAL NOT NULL DEFAULT 2.0,
  last_cleaned_at TEXT,
  active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS bin_readings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  bin_id TEXT NOT NULL REFERENCES bins(bin_id),
  fill_pct REAL NOT NULL,
  recorded_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  bin_id TEXT NOT NULL REFERENCES bins(bin_id),
  user_id INTEGER NOT NULL REFERENCES users(id),
  tag TEXT, comment TEXT, photo_path TEXT,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','resolved')),
  upvotes INTEGER NOT NULL DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  resolved_at TEXT
);
CREATE TABLE IF NOT EXISTS clean_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  bin_id TEXT NOT NULL REFERENCES bins(bin_id),
  admin_id INTEGER NOT NULL REFERENCES users(id),
  fill_before REAL,
  cleaned_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS follows (
  user_id INTEGER NOT NULL REFERENCES users(id),
  bin_id TEXT NOT NULL REFERENCES bins(bin_id),
  PRIMARY KEY (user_id, bin_id)
);
CREATE TABLE IF NOT EXISTS notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id),
  bin_id TEXT REFERENCES bins(bin_id),
  message TEXT NOT NULL,
  is_read INTEGER NOT NULL DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS reuse_requests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER REFERENCES users(id),
  item TEXT NOT NULL, ai_response_json TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS adopted_ideas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id),
  item TEXT, idea_title TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS submissions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id),
  idea_title TEXT, materials TEXT, description TEXT,
  process_photo_path TEXT, photo_path TEXT,
  image_hash TEXT, process_hash TEXT,
  ai_json TEXT, ai_score REAL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
  reviewed_by INTEGER REFERENCES users(id),
  review_note TEXT,
  points_awarded INTEGER NOT NULL DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  reviewed_at TEXT
);
CREATE TABLE IF NOT EXISTS submission_flags (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  submission_id INTEGER NOT NULL REFERENCES submissions(id),
  user_id INTEGER NOT NULL REFERENCES users(id),
  reason TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (submission_id, user_id)
);
CREATE TABLE IF NOT EXISTS points_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id),
  points INTEGER NOT NULL, reason TEXT, ref_id TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS report_votes (
  report_id INTEGER NOT NULL REFERENCES reports(id),
  user_id INTEGER NOT NULL REFERENCES users(id),
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (report_id, user_id)
);

"""



@contextmanager
def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()



def migrate(conn):
    """Add columns that were introduced after the first version of the schema."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(submissions)")}
    if "daily_code" not in cols:
        conn.execute("ALTER TABLE submissions ADD COLUMN daily_code TEXT")
    if "flag_review" not in cols:
        conn.execute("ALTER TABLE submissions ADD COLUMN flag_review INTEGER NOT NULL DEFAULT 0")


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        migrate(conn)