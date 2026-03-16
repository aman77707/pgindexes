"""
Seed data for the GIN index demo.

Articles cover a range of technology topics so that full-text search
queries return varied, interesting result sets.

Products carry rich JSONB attributes (brand, category, tags, specs) that
let us illustrate several flavours of the @> containment operator.
"""

from __future__ import annotations

import psycopg2.extensions

from pgindexes.db import cursor

_ARTICLES = [
    (
        "Introduction to PostgreSQL",
        "PostgreSQL is a powerful, open-source relational database system. "
        "It supports advanced SQL features, full-text search, and JSONB storage. "
        "Many teams choose PostgreSQL over MySQL for its rich feature set and "
        "standards compliance.",
    ),
    (
        "Getting Started with Python",
        "Python is a high-level, interpreted programming language known for its "
        "readability and simplicity. It is widely used in web development, data "
        "science, machine learning, and scripting. The Python ecosystem has "
        "thousands of packages available on PyPI.",
    ),
    (
        "Machine Learning with Python and scikit-learn",
        "Machine learning enables computers to learn from data without being "
        "explicitly programmed. Python's scikit-learn library provides simple "
        "and efficient tools for classification, regression, and clustering. "
        "Neural networks and deep learning have extended these capabilities further.",
    ),
    (
        "Full-Text Search in PostgreSQL",
        "PostgreSQL provides built-in full-text search through tsvector and tsquery "
        "types. GIN indexes make these searches extremely fast even on millions of "
        "documents. This feature competes with dedicated search engines like "
        "Elasticsearch for many common use cases.",
    ),
    (
        "Docker and Container Orchestration",
        "Docker packages applications into lightweight, portable containers. "
        "Kubernetes orchestrates fleets of containers across multiple hosts. "
        "Container technology has transformed how teams deploy and scale services "
        "in production environments.",
    ),
    (
        "Building REST APIs with FastAPI",
        "FastAPI is a modern Python web framework for building REST APIs quickly. "
        "It uses Python type hints to generate interactive documentation automatically. "
        "FastAPI is built on Starlette and Pydantic, offering async support out of the box.",
    ),
    (
        "Elasticsearch vs PostgreSQL Full-Text Search",
        "Elasticsearch is a dedicated search engine built on Apache Lucene. "
        "PostgreSQL's GIN-indexed tsvector offers comparable search quality for "
        "many workloads while keeping your stack simple. Avoiding a separate search "
        "cluster reduces operational overhead and data synchronisation complexity.",
    ),
    (
        "Understanding Database Indexes",
        "Database indexes speed up query execution by maintaining auxiliary data "
        "structures. B-tree indexes suit range and equality queries. GIN indexes "
        "excel at full-text and JSONB containment searches. Choosing the right "
        "index type is critical for query performance.",
    ),
    (
        "JSONB in PostgreSQL: Schemaless Data Done Right",
        "JSONB stores JSON data in a decomposed binary format enabling efficient "
        "lookups and GIN indexing. Unlike plain JSON, JSONB supports operators "
        "such as @>, <@, ?, ?|, and ?& for containment and key-existence checks. "
        "It bridges the gap between relational and document databases.",
    ),
    (
        "Scaling Postgres with Read Replicas",
        "Read replicas allow you to distribute read-heavy workloads across multiple "
        "PostgreSQL instances. Logical replication streams changes from the primary "
        "to replicas in near real-time. Connection poolers like PgBouncer sit in "
        "front of the replica pool to manage connections efficiently.",
    ),
]

_PRODUCTS = [
    (
        "Dell XPS 15 Laptop",
        {
            "brand": "Dell",
            "category": "electronics",
            "subcategory": "laptops",
            "tags": ["laptop", "ultrabook", "windows"],
            "features": ["ssd", "touchscreen", "backlit-keyboard"],
            "specs": {"ram_gb": 32, "storage_gb": 512, "display_inch": 15.6},
            "price_range": "premium",
            "in_stock": True,
        },
    ),
    (
        "Apple MacBook Pro 14",
        {
            "brand": "Apple",
            "category": "electronics",
            "subcategory": "laptops",
            "tags": ["laptop", "macOS", "apple-silicon"],
            "features": ["ssd", "retina-display", "touch-id", "magsafe"],
            "specs": {"ram_gb": 16, "storage_gb": 512, "display_inch": 14.2},
            "price_range": "premium",
            "in_stock": True,
        },
    ),
    (
        "Samsung Galaxy S24",
        {
            "brand": "Samsung",
            "category": "electronics",
            "subcategory": "smartphones",
            "tags": ["smartphone", "android", "5g"],
            "features": ["5g", "face-unlock", "wireless-charging", "amoled"],
            "specs": {"ram_gb": 8, "storage_gb": 256, "display_inch": 6.2},
            "price_range": "premium",
            "in_stock": True,
        },
    ),
    (
        "Apple iPhone 15",
        {
            "brand": "Apple",
            "category": "electronics",
            "subcategory": "smartphones",
            "tags": ["smartphone", "iOS", "5g"],
            "features": ["5g", "face-id", "wireless-charging", "ceramic-shield"],
            "specs": {"ram_gb": 6, "storage_gb": 128, "display_inch": 6.1},
            "price_range": "premium",
            "in_stock": False,
        },
    ),
    (
        "Logitech MX Master 3 Mouse",
        {
            "brand": "Logitech",
            "category": "electronics",
            "subcategory": "peripherals",
            "tags": ["mouse", "wireless", "ergonomic"],
            "features": ["wireless", "usb-c-charging", "multi-device"],
            "specs": {"dpi": 8000, "buttons": 7},
            "price_range": "mid",
            "in_stock": True,
        },
    ),
    (
        "Sony WH-1000XM5 Headphones",
        {
            "brand": "Sony",
            "category": "electronics",
            "subcategory": "audio",
            "tags": ["headphones", "noise-cancelling", "wireless"],
            "features": ["anc", "wireless", "usb-c-charging", "30hr-battery"],
            "specs": {"driver_mm": 30, "frequency_hz": [4, 40000]},
            "price_range": "premium",
            "in_stock": True,
        },
    ),
    (
        "Kindle Paperwhite",
        {
            "brand": "Amazon",
            "category": "electronics",
            "subcategory": "e-readers",
            "tags": ["e-reader", "kindle", "waterproof"],
            "features": ["e-ink", "backlit", "waterproof", "wifi"],
            "specs": {"storage_gb": 8, "display_inch": 6.8},
            "price_range": "budget",
            "in_stock": True,
        },
    ),
    (
        "IKEA KALLAX Shelf Unit",
        {
            "brand": "IKEA",
            "category": "furniture",
            "subcategory": "shelving",
            "tags": ["shelf", "storage", "modular"],
            "features": ["modular", "wall-mountable"],
            "specs": {"width_cm": 77, "height_cm": 147, "compartments": 8},
            "price_range": "budget",
            "in_stock": True,
        },
    ),
    (
        "Dell UltraSharp 27 Monitor",
        {
            "brand": "Dell",
            "category": "electronics",
            "subcategory": "monitors",
            "tags": ["monitor", "4k", "usb-c"],
            "features": ["4k", "usb-c", "hdr", "pivot"],
            "specs": {"ram_gb": None, "display_inch": 27, "resolution": "3840x2160"},
            "price_range": "premium",
            "in_stock": True,
        },
    ),
    (
        "Budget Wireless Earbuds",
        {
            "brand": "Anker",
            "category": "electronics",
            "subcategory": "audio",
            "tags": ["earbuds", "wireless", "budget"],
            "features": ["wireless", "usb-c-charging", "ipx5"],
            "specs": {"driver_mm": 11, "battery_hr": 8},
            "price_range": "budget",
            "in_stock": True,
        },
    ),
]


def seed(conn: psycopg2.extensions.connection) -> None:
    """Insert sample data only when the tables are empty."""
    with cursor(conn, dict_cursor=False) as cur:
        cur.execute("SELECT COUNT(*) FROM articles;")
        article_count = cur.fetchone()[0]  # type: ignore[index]

        cur.execute("SELECT COUNT(*) FROM products;")
        product_count = cur.fetchone()[0]  # type: ignore[index]

    if article_count == 0:
        with cursor(conn) as cur:
            cur.executemany(
                "INSERT INTO articles (title, body) VALUES (%s, %s);",
                _ARTICLES,
            )
        print(f"[seed] Inserted {len(_ARTICLES)} articles.")
    else:
        print(f"[seed] articles already has {article_count} row(s) — skipping.")

    if product_count == 0:
        with cursor(conn) as cur:
            cur.executemany(
                "INSERT INTO products (name, attributes) VALUES (%s, %s::jsonb);",
                [(name, __import__("json").dumps(attrs)) for name, attrs in _PRODUCTS],
            )
        print(f"[seed] Inserted {len(_PRODUCTS)} products.")
    else:
        print(f"[seed] products already has {product_count} row(s) — skipping.")

    print()
