"""
Base de datos SQLite local para ALBA Offline.
Reemplaza a Supabase PostgreSQL.
"""
import sqlite3
import os
from pathlib import Path
import pandas as pd

_DB_PATH = os.environ.get(
    "ALBA_DB_PATH",
    str(Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "alba_offline.db"),
)

_conn = None


def get_connection() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
    return _conn


def query_all(table_name: str, limit: int = None) -> list[dict]:
    conn = get_connection()
    sql = f"SELECT * FROM {table_name}"
    if limit:
        sql += f" LIMIT {limit}"
    cursor = conn.execute(sql)
    return [dict(row) for row in cursor.fetchall()]


def query_sql(sql: str, params: tuple = None) -> list[dict]:
    conn = get_connection()
    cursor = conn.execute(sql, params or ())
    return [dict(row) for row in cursor.fetchall()]


def query_one(sql: str, params: tuple = None) -> dict | None:
    conn = get_connection()
    cursor = conn.execute(sql, params or ())
    row = cursor.fetchone()
    return dict(row) if row else None


def insert(table_name: str, data: dict) -> int:
    conn = get_connection()
    cols = ", ".join(data.keys())
    placeholders = ", ".join(["?"] * len(data))
    sql = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})"
    cursor = conn.execute(sql, tuple(data.values()))
    conn.commit()
    return cursor.lastrowid


def table_exists(table_name: str) -> bool:
    conn = get_connection()
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    return cursor.fetchone() is not None


def list_tables() -> list[str]:
    conn = get_connection()
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    return [row[0] for row in cursor.fetchall()]


def table_count(table_name: str) -> int:
    conn = get_connection()
    cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
    return cursor.fetchone()[0]