"""
JSONB containment demo using GIN index + @> operator.

Why GIN for JSONB?
  PostgreSQL decomposes a JSONB value into a set of (key, value) path entries
  and stores them in a GIN index.  The @> (contains) operator can then locate
  rows that match a partial document in O(log n) time instead of scanning
  every row and parsing JSON.  This is the same technique document databases
  (MongoDB, Elasticsearch) use for document lookups.

Operators demonstrated
  @>    — containment: left JSONB contains all key/value pairs in right JSONB
  ?     — key existence: does this JSONB have a top-level key?
  ?|    — any-key: does this JSONB have any of the listed top-level keys?
  ?&    — all-keys: does this JSONB have ALL of the listed top-level keys?

All these operators are accelerated by the same GIN index on the 'attributes'
column — no separate indexes are required.
"""

from __future__ import annotations

import json

import psycopg2.extensions

from pgindexes.db import cursor

_DIVIDER = "-" * 72


def _print_results(rows: list[dict], label: str, operator: str) -> None:
    print(f"  Operator : {operator}")
    print(f"  Filter   : {label}")
    print(f"  Results  : {len(rows)} row(s)")
    for row in rows:
        attrs = row.get("attributes", {})
        brand = attrs.get("brand", "—")
        price = attrs.get("price_range", "—")
        stock = "✓" if attrs.get("in_stock") else "✗"
        print(
            f"    • [{row['id']:>2}] {row['name']:40s}  brand={brand:<10} price={price:<8} stock={stock}"
        )
    print()


# ---------------------------------------------------------------------------
# Individual query demonstrations
# ---------------------------------------------------------------------------


def demo_simple_containment(conn: psycopg2.extensions.connection) -> None:
    """
    @> with a single key/value pair.

    Finds all JSONB documents where a specific key has a specific value.
    Equivalent to a WHERE clause on a regular column, but for schemaless data.
    """
    print("── @>  simple key/value containment ───────────────────────────────────")

    filters = [
        ({"brand": "Dell"}, "brand = Dell"),
        ({"brand": "Apple"}, "brand = Apple"),
        ({"price_range": "premium"}, "price_range = premium"),
        ({"price_range": "budget"}, "price_range = budget"),
        ({"in_stock": False}, "in_stock = false"),
        ({"category": "electronics"}, "category = electronics"),
        ({"category": "furniture"}, "category = furniture"),
    ]

    for doc, label in filters:
        with cursor(conn) as cur:
            cur.execute(
                """
                SELECT id, name, attributes
                FROM   products
                WHERE  attributes @> %s::jsonb
                ORDER  BY id;
                """,
                (json.dumps(doc),),
            )
            rows = [dict(r) for r in cur.fetchall()]
        _print_results(rows, label, "@>")


def demo_nested_containment(conn: psycopg2.extensions.connection) -> None:
    """
    @> with nested objects — match on a sub-document.

    The right-hand side can be any partial JSONB document, including nested keys.
    """
    print("── @>  nested object containment ───────────────────────────────────────")

    filters = [
        (
            {"brand": "Dell", "category": "electronics"},
            "brand=Dell AND category=electronics",
        ),
        (
            {"brand": "Apple", "price_range": "premium"},
            "brand=Apple AND price_range=premium",
        ),
        (
            {"subcategory": "smartphones", "price_range": "premium"},
            "subcategory=smartphones AND price_range=premium",
        ),
    ]

    for doc, label in filters:
        with cursor(conn) as cur:
            cur.execute(
                """
                SELECT id, name, attributes
                FROM   products
                WHERE  attributes @> %s::jsonb
                ORDER  BY id;
                """,
                (json.dumps(doc),),
            )
            rows = [dict(r) for r in cur.fetchall()]
        _print_results(rows, label, "@>  (multi-key)")


def demo_array_containment(conn: psycopg2.extensions.connection) -> None:
    """
    @> with arrays inside JSONB.

    When the value is an array, @> checks that every element on the right
    appears somewhere in the left array.  This gives a powerful 'has tag'
    or 'has feature' query pattern.
    """
    print("── @>  array containment (features / tags) ─────────────────────────────")

    filters = [
        ({"features": ["ssd"]}, "has feature: ssd"),
        ({"features": ["wireless"]}, "has feature: wireless"),
        ({"features": ["usb-c-charging"]}, "has feature: usb-c-charging"),
        ({"features": ["5g"]}, "has feature: 5g"),
        ({"tags": ["laptop"]}, "has tag: laptop"),
        ({"tags": ["wireless", "budget"]}, "has both tags: wireless AND budget"),
        ({"features": ["wireless", "anc"]}, "has both features: wireless AND anc"),
    ]

    for doc, label in filters:
        with cursor(conn) as cur:
            cur.execute(
                """
                SELECT id, name, attributes
                FROM   products
                WHERE  attributes @> %s::jsonb
                ORDER  BY id;
                """,
                (json.dumps(doc),),
            )
            rows = [dict(r) for r in cur.fetchall()]
        _print_results(rows, label, "@>  (array)")


def demo_key_existence(conn: psycopg2.extensions.connection) -> None:
    """
    ?, ?|, ?& — key-existence operators.

    These check for the presence of top-level keys regardless of value.
    Also covered by the GIN index.
    """
    print("── ?  /  ?|  /  ?&  key-existence operators ────────────────────────────")

    with cursor(conn) as cur:
        # ? — single key exists
        cur.execute(
            "SELECT id, name FROM products WHERE attributes ? 'subcategory' ORDER BY id;"
        )
        rows = [dict(r) for r in cur.fetchall()]
    print("  Operator : ?  (key exists)")
    print("  Filter   : has top-level key 'subcategory'")
    print(f"  Results  : {len(rows)} row(s)  — {[r['name'] for r in rows]}\n")

    with cursor(conn) as cur:
        # ?| — any of these keys exist
        cur.execute(
            "SELECT id, name FROM products WHERE attributes ?| ARRAY['subcategory','specs'] ORDER BY id;"
        )
        rows = [dict(r) for r in cur.fetchall()]
    print("  Operator : ?|  (any key exists)")
    print("  Filter   : has 'subcategory' OR 'specs'")
    print(f"  Results  : {len(rows)} row(s)  — {[r['name'] for r in rows]}\n")

    with cursor(conn) as cur:
        # ?& — all of these keys must exist
        cur.execute(
            "SELECT id, name FROM products WHERE attributes ?& ARRAY['brand','features','specs'] ORDER BY id;"
        )
        rows = [dict(r) for r in cur.fetchall()]
    print("  Operator : ?&  (all keys exist)")
    print("  Filter   : has 'brand' AND 'features' AND 'specs'")
    print(f"  Results  : {len(rows)} row(s)  — {[r['name'] for r in rows]}\n")


def demo_explain(conn: psycopg2.extensions.connection) -> None:
    """Show EXPLAIN to confirm the GIN index is used for @> queries."""
    print("── EXPLAIN: GIN index usage ────────────────────────────────────────────")
    with cursor(conn, dict_cursor=False) as cur:
        cur.execute(
            """
            EXPLAIN (FORMAT TEXT)
            SELECT id, name
            FROM   products
            WHERE  attributes @> '{"brand": "Dell"}'::jsonb;
            """
        )
        plan = "\n".join(row[0] for row in cur.fetchall())
    print(plan)
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run(conn: psycopg2.extensions.connection) -> None:
    """Run all JSONB GIN index demonstrations."""
    print(_DIVIDER)
    print("DEMO 2 — JSONB Containment with GIN index (@> operator)")
    print(_DIVIDER)
    print(
        "\nThe 'products' table has a JSONB 'attributes' column indexed with GIN.\n"
        "All queries below use @>, ?, ?|, ?& and are served from the index.\n"
    )
    demo_explain(conn)
    demo_simple_containment(conn)
    demo_nested_containment(conn)
    demo_array_containment(conn)
    demo_key_existence(conn)
