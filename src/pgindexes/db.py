"""Database connection helpers."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

import psycopg2
import psycopg2.extensions
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()


def ensure_database() -> None:
    """
    Connect to the postgres maintenance database and create the target
    database (POSTGRES_DB) if it does not already exist.

    CREATE DATABASE cannot run inside a transaction block, so we use a
    dedicated short-lived connection with autocommit=True.
    """
    target_db = os.getenv("POSTGRES_DB", "pgindexes")
    maintenance_conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname="postgres",  # always exists
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
    )
    maintenance_conn.autocommit = True  # required for CREATE DATABASE
    try:
        with maintenance_conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s;",
                (target_db,),
            )
            exists = cur.fetchone() is not None
        if not exists:
            with maintenance_conn.cursor() as cur:
                cur.execute(f'CREATE DATABASE "{target_db}";')
            print(f"[db] Database '{target_db}' created.")
        else:
            print(f"[db] Database '{target_db}' already exists.")
    finally:
        maintenance_conn.close()


def get_connection() -> psycopg2.extensions.connection:
    """Return a new psycopg2 connection using env-var credentials."""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "pgindexes"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
    )


@contextmanager
def cursor(
    conn: psycopg2.extensions.connection,
    *,
    dict_cursor: bool = True,
) -> Generator[psycopg2.extensions.cursor, None, None]:
    """Yield a cursor and commit/rollback automatically."""
    factory = psycopg2.extras.RealDictCursor if dict_cursor else None
    cur = conn.cursor(cursor_factory=factory)  # type: ignore[call-arg]
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
