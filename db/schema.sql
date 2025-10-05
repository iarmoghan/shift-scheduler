PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS app_user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('ADMIN','VOLUNTEER')),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS shift (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  location TEXT NOT NULL,
  starts_at TEXT NOT NULL,  -- ISO string
  ends_at TEXT NOT NULL,
  capacity INTEGER NOT NULL CHECK (capacity >= 0),
  status TEXT NOT NULL DEFAULT 'Published'
         CHECK (status IN ('Draft','Published','Full','InProgress','Completed','Cancelled')),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS signup (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  shift_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  UNIQUE (shift_id, user_id),
  FOREIGN KEY (shift_id) REFERENCES shift(id)    ON DELETE CASCADE,
  FOREIGN KEY (user_id)  REFERENCES app_user(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS waitlist (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  shift_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  UNIQUE (shift_id, user_id),
  FOREIGN KEY (shift_id) REFERENCES shift(id)    ON DELETE CASCADE,
  FOREIGN KEY (user_id)  REFERENCES app_user(id) ON DELETE CASCADE
);
