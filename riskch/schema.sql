-- Initialize the database.
-- Drop any existing data and create empty tables.

DROP TABLE IF EXISTS marketpool;
DROP TABLE IF EXISTS hist;
DROP TABLE IF EXISTS eq_safef;

CREATE TABLE marketpool (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  issue TEXT NOT NULL,
  fromdate DATE NOT NULL,
  todate DATE NOT NULL,
  car25 REAL NOT NULL DEFAULT 0.0,
  safef REAL NOT NULL DEFAULT 0.0,
  cor2bench REAL NOT NULL DEFAULT 0.0
);

CREATE TABLE hist (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  issue_id INTEGER NOT NULL,
  trade_id INTEGER NOT NULL,
  close_d REAL NOT NULL,
  retrun_d REAL NOT NULL DEFAULT 0.0,
  pnl REAL NOT NULL DEFAULT 0.0,
  FOREIGN KEY (issue_id) REFERENCES marketpool (id)
);

CREATE TABLE eq_safef (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  issue_id INTEGER NOT NULL,
  curve TEXT NOT NULL,
  FOREIGN KEY (issue_id) REFERENCES marketpool (id)
);