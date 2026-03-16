"""
Full-Text Search demo using GIN index + tsvector + @@ operator.

Why GIN for FTS?
  PostgreSQL stores pre-processed lexemes in a TSVECTOR column and builds a
  GIN (Generalized Inverted Index) on top.  A GIN maps every lexeme to the
  set of row-ids that contain it — exactly the same data structure used by
  dedicated search engines like Elasticsearch (which calls it an "inverted
  index").  The @@ match operator consults the GIN index directly, so only
  matching rows are touched regardless of table size.

Operators & functions used
  @@                     — text-search match: tsvector @@ tsquery
  to_tsquery()           — strict tsquery parser (lexemes, &, |, !)
  plainto_tsquery()      — plain English → AND query
  websearch_to_tsquery() — Google-style: phrases, -, OR
  ts_rank()              — relevance score (0–1)
  ts_headline()          — highlight matched terms in the original text
"""

from __future__ import annotations

import psycopg2.extensions

from pgindexes.db import cursor

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DIVIDER = "-" * 72


def _print_results(rows: list[dict], label: str) -> None:
    print(f"  → {len(rows)} result(s) for: {label}")
    for row in rows:
        rank = f"  [rank={row['rank']:.4f}]" if "rank" in row else ""
        print(f"    • [{row['id']:>2}] {row['title']}{rank}")
        if "headline" in row:
            print(f"           {row['headline']}")
    print()


# ---------------------------------------------------------------------------
# Individual query demonstrations
# ---------------------------------------------------------------------------


def demo_to_tsquery(conn: psycopg2.extensions.connection) -> None:
    """
    to_tsquery — strict query syntax.

    Lexemes must be valid; AND (&), OR (|), NOT (!) and phrase (<->) operators
    are available.  The GIN index is used for all operators.
    """
    print("── to_tsquery ──────────────────────────────────────────────────────────")

    queries = [
        # AND: both lexemes must appear
        ("postgresql & index", "articles about PostgreSQL AND indexes"),
        # OR: either lexeme
        ("docker | kubernetes", "Docker OR Kubernetes mentions"),
        # phrase: 'machine' immediately followed by 'learn'
        ("machine <-> learn", "exact phrase 'machine learning'"),
        # NOT: exclude rows containing 'elasticsearch'
        ("postgresql & !elasticsearch", "PostgreSQL but NOT Elasticsearch"),
    ]

    for tsq, label in queries:
        with cursor(conn) as cur:
            cur.execute(
                """
                SELECT id,
                       title,
                       ts_rank(search_vector, query) AS rank
                FROM   articles,
                       to_tsquery('english', %s) AS query
                WHERE  search_vector @@ query
                ORDER  BY rank DESC;
                """,
                (tsq,),
            )
            rows = [dict(r) for r in cur.fetchall()]
        _print_results(rows, f"to_tsquery('{tsq}')  — {label}")


def demo_plainto_tsquery(conn: psycopg2.extensions.connection) -> None:
    """
    plainto_tsquery — plain prose converted to an AND-query.

    Every word becomes a lexeme joined by &.  No special syntax needed.
    Great for user-supplied search boxes.
    """
    print("── plainto_tsquery ─────────────────────────────────────────────────────")

    phrases = [
        "full text search database",
        "python machine learning scikit",
        "REST API web framework",
    ]

    for phrase in phrases:
        with cursor(conn) as cur:
            cur.execute(
                """
                SELECT id,
                       title,
                       ts_rank(search_vector, query) AS rank
                FROM   articles,
                       plainto_tsquery('english', %s) AS query
                WHERE  search_vector @@ query
                ORDER  BY rank DESC;
                """,
                (phrase,),
            )
            rows = [dict(r) for r in cur.fetchall()]
        _print_results(rows, f"plainto_tsquery('{phrase}')")


def demo_websearch_to_tsquery(conn: psycopg2.extensions.connection) -> None:
    """
    websearch_to_tsquery — Google-style syntax.

    Quoted phrases, -exclusions, and OR are supported.  This is the most
    user-friendly form and safe to expose to end-users directly.
    """
    print("── websearch_to_tsquery ────────────────────────────────────────────────")

    web_queries = [
        ('"full text search" postgresql', "exact phrase + extra term"),
        ("python -javascript", "Python but exclude JavaScript"),
        ("docker OR kubernetes container", "Docker or Kubernetes about containers"),
    ]

    for wq, label in web_queries:
        with cursor(conn) as cur:
            cur.execute(
                """
                SELECT id,
                       title,
                       ts_rank(search_vector, query)         AS rank,
                       ts_headline('english', body, query,
                                   'MaxWords=15, MinWords=5,
                                    StartSel=>>>, StopSel=<<<')
                                                             AS headline
                FROM   articles,
                       websearch_to_tsquery('english', %s) AS query
                WHERE  search_vector @@ query
                ORDER  BY rank DESC;
                """,
                (wq,),
            )
            rows = [dict(r) for r in cur.fetchall()]
        _print_results(rows, f"websearch_to_tsquery('{wq}')  — {label}")


def demo_explain(conn: psycopg2.extensions.connection) -> None:
    """
    Show EXPLAIN output to confirm the GIN index is being used.
    """
    print("── EXPLAIN: GIN index usage ────────────────────────────────────────────")
    with cursor(conn, dict_cursor=False) as cur:
        cur.execute(
            """
            EXPLAIN (FORMAT TEXT)
            SELECT id, title
            FROM   articles
            WHERE  search_vector @@ plainto_tsquery('english', 'postgresql index');
            """
        )
        plan = "\n".join(row[0] for row in cur.fetchall())
    print(plan)
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run(conn: psycopg2.extensions.connection) -> None:
    """Run all full-text search demonstrations."""
    print(_DIVIDER)
    print("DEMO 1 — Full-Text Search with GIN index (tsvector + @@ operator)")
    print(_DIVIDER)
    print(
        "\nThe 'articles' table has a stored TSVECTOR column indexed with GIN.\n"
        "All queries below use the @@ operator and are served from the index.\n"
    )
    demo_explain(conn)
    demo_to_tsquery(conn)
    demo_plainto_tsquery(conn)
    demo_websearch_to_tsquery(conn)
