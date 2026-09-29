"""SQLite storage layer.

The schema is created from the DDL below. Repositories in ``repositories.py``
are the only place that touches this connection, so the storage engine can be
swapped for PostgreSQL + pgvector later without changing service code.
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from config import settings
from utils import get_logger

logger = get_logger("database")

SCHEMA = """
CREATE TABLE IF NOT EXISTS standards (
    id                  TEXT PRIMARY KEY,
    standard_number     TEXT NOT NULL,
    title               TEXT NOT NULL,
    scope               TEXT,
    category            TEXT,
    version             TEXT,
    status              TEXT DEFAULT 'Active',
    certification       TEXT,
    source_url          TEXT,
    standard_types      TEXT,
    product_types       TEXT,
    materials           TEXT,
    applications        TEXT,
    requirements        TEXT,
    testing             TEXT,
    safety              TEXT,
    installation        TEXT,
    amendments          TEXT,
    related_standards   TEXT,
    referenced_standards TEXT,
    superseded_by       TEXT,
    source              TEXT,
    bis_verified        INTEGER DEFAULT 0,
    created_at          TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS standard_relationships (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    source_standard     TEXT NOT NULL,
    target_standard     TEXT NOT NULL,
    relationship_type   TEXT NOT NULL,
    UNIQUE (source_standard, target_standard, relationship_type)
);
CREATE INDEX IF NOT EXISTS idx_rel_source ON standard_relationships (source_standard);
CREATE INDEX IF NOT EXISTS idx_rel_target ON standard_relationships (target_standard);

CREATE TABLE IF NOT EXISTS documents (
    id                  TEXT PRIMARY KEY,
    filename            TEXT NOT NULL,
    original_filename   TEXT,
    extracted_text      TEXT,
    page_count          INTEGER DEFAULT 0,
    char_count          INTEGER DEFAULT 0,
    is_scanned          INTEGER DEFAULT 0,
    extraction_status   TEXT DEFAULT 'ok',
    source_type         TEXT DEFAULT 'pdf',
    uploaded_at         TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS extracted_requirements (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id         TEXT NOT NULL,
    product             TEXT,
    category            TEXT,
    intended_use        TEXT,
    materials           TEXT,
    technical_requirements    TEXT,
    performance_requirements  TEXT,
    safety_requirements       TEXT,
    testing_requirements      TEXT,
    installation_requirements TEXT,
    certification_requirements TEXT,
    extraction_method   TEXT,
    created_at          TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_req_document ON extracted_requirements (document_id);

CREATE TABLE IF NOT EXISTS recommendations (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id         TEXT NOT NULL,
    standard_id         TEXT NOT NULL,
    score               REAL,
    category            TEXT,
    explanation         TEXT,
    matched_requirements TEXT,
    missing_requirements TEXT,
    related_standards   TEXT,
    validation_status   TEXT,
    created_at          TEXT DEFAULT (datetime('now')),
    UNIQUE (document_id, standard_id),
    FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_rec_document ON recommendations (document_id);

CREATE TABLE IF NOT EXISTS specification_gaps (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id         TEXT NOT NULL,
    gap_type            TEXT,
    severity            TEXT,
    description         TEXT,
    suggested_action    TEXT,
    related_standards   TEXT,
    created_at          TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_gap_document ON specification_gaps (document_id);
"""


class Database:
    """Thread-safe SQLite connection manager."""

    def __init__(self, path: Path | str = settings.database_path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._local = threading.local()
        self._initialise()

    # -- connection handling ------------------------------------------------
    @property
    def connection(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            self._local.conn = conn
        return conn

    @contextmanager
    def cursor(self) -> Iterator[sqlite3.Cursor]:
        with self._lock:
            cur = self.connection.cursor()
            try:
                yield cur
                self.connection.commit()
            except Exception:
                self.connection.rollback()
                raise
            finally:
                cur.close()

    def _initialise(self) -> None:
        with self.cursor() as cur:
            cur.executescript(SCHEMA)
            self._migrate(cur)
        logger.info("database ready at %s", self.path)

    @staticmethod
    def _migrate(cur: sqlite3.Cursor) -> None:
        """Add columns introduced after a database file was first created."""
        existing = {row["name"] for row in cur.execute("PRAGMA table_info(standards)").fetchall()}
        for column, ddl in (
            ("bis_verified", "ALTER TABLE standards ADD COLUMN bis_verified INTEGER DEFAULT 0"),
        ):
            if existing and column not in existing:
                cur.execute(ddl)
                logger.info("migrated standards.%s", column)

    # -- helpers ------------------------------------------------------------
    def execute(self, sql: str, params: tuple | list = ()) -> sqlite3.Cursor:
        with self.cursor() as cur:
            cur.execute(sql, params)
            return cur

    def query_all(self, sql: str, params: tuple | list = ()) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]

    def query_one(self, sql: str, params: tuple | list = ()) -> dict | None:
        with self.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None

    def truncate_analysis_tables(self) -> None:
        """Clear documents/recommendations/gaps while keeping the standards catalogue."""
        with self.cursor() as cur:
            cur.execute("DELETE FROM recommendations")
            cur.execute("DELETE FROM specification_gaps")
            cur.execute("DELETE FROM extracted_requirements")
            cur.execute("DELETE FROM documents")
        logger.info("analysis tables cleared")


db = Database()
