"""
DDL for the GIN index demo.

Two tables are created:

  articles  — has a stored TSVECTOR column that is kept in sync with the
               title + body text.  A GIN index on that column enables
               lightning-fast full-text search via the @@ operator.

  products  — stores semi-structured data in a JSONB column.  A GIN index
               on that column enables containment queries via the @> operator
               without scanning every row.
"""

from __future__ import annotations

import psycopg2.extensions

from pgindexes.db import cursor


def setup(conn: psycopg2.extensions.connection) -> None:
    """Ensure demo tables and GIN indexes exist (idempotent — never drops data)."""
    with cursor(conn) as cur:
        # ------------------------------------------------------------------
        # articles — full-text search demo (tsvector + @@)
        # ------------------------------------------------------------------
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS articles (
                id            SERIAL PRIMARY KEY,
                title         TEXT NOT NULL,
                body          TEXT NOT NULL,
                -- Stored, auto-updated tsvector: always consistent with the text.
                -- Combines title (weight A = highest) and body (weight B).
                search_vector TSVECTOR
                    GENERATED ALWAYS AS (
                        setweight(to_tsvector('english', title), 'A') ||
                        setweight(to_tsvector('english', body),  'B')
                    ) STORED
            );
            """
        )
        # GIN index on the pre-computed tsvector — used by @@ queries.
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_articles_search_vector
                ON articles USING GIN (search_vector);
            """
        )

        # ------------------------------------------------------------------
        # products — JSONB containment demo (@>)
        # ------------------------------------------------------------------
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id         SERIAL PRIMARY KEY,
                name       TEXT NOT NULL,
                -- Semi-structured attributes: brand, category, tags, specs …
                attributes JSONB NOT NULL DEFAULT '{}'
            );
            """
        )
        # GIN index on the JSONB column — used by @> / <@ / ? / ?| / ?& operators.
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_products_attributes
                ON products USING GIN (attributes);
            """
        )

    print("[schema] Tables and GIN indexes are ready.\n")
