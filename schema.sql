-- users
CREATE TABLE IF NOT EXISTS app_user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('ADMIN','VOLUNTEER'))
);

-- shifts
CREATE TABLE IF NOT EXISTS shift (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  location TEXT,
  starts_at TEXT NOT NULL,   -- ISO datetime string
  ends_at   TEXT NOT NULL,
  capacity  INTEGER NOT NULL DEFAULT 1
);

-- signups (unique per user per shift) -- used in next step
CREATE TABLE IF NOT EXISTS signup (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  shift_id INTEGER NOT NULL REFERENCES shift(id) ON DELETE CASCADE,
  user_id  INTEGER NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (shift_id, user_id)
);
