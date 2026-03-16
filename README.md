# pgindexes

Postgres indexes prototypes — exploring how the right index type can replace
a dedicated external service and keep your stack simple.

---

## Demos

### GIN — Generalized Inverted Index

> **Thesis:** PostgreSQL's GIN index brings core Elasticsearch capabilities
> into your existing database, eliminating the operational cost of running and
> syncing a separate search cluster for many common workloads.

The demo lives in `src/pgindexes/gin/` and exercises two GIN use-cases:

| Use-case | Table | Column type | Operator |
|---|---|---|---|
| Full-text search | `articles` | `TSVECTOR` (stored, generated) | `@@` |
| Document containment search | `products` | `JSONB` | `@>`, `?`, `?|`, `?&` |

#### Full-text search (`tsvector` + `@@`)

The `articles` table carries a **stored generated `TSVECTOR` column** that
is kept in sync automatically whenever `title` or `body` changes.  A GIN
index on that column gives sub-millisecond search on large document sets.

```sql
-- GIN index
CREATE INDEX idx_articles_search_vector
    ON articles USING GIN (search_vector);

-- Match with @@
SELECT title, ts_rank(search_vector, query) AS rank
FROM   articles, plainto_tsquery('english', 'postgresql full text search') AS query
WHERE  search_vector @@ query
ORDER  BY rank DESC;
```

Three query builders are demonstrated:

| Function | Syntax | Best for |
|---|---|---|
| `to_tsquery` | `'machine & learn'`, `'docker \| k8s'`, `'machine <-> learn'` | Programmatic queries |
| `plainto_tsquery` | `'full text search postgres'` | Simple search boxes |
| `websearch_to_tsquery` | `'"full text" -elasticsearch'` | User-facing search |

#### JSONB containment (`@>`)

The `products` table stores semi-structured data (brand, category, features,
specs …) in a **JSONB column**.  A single GIN index covers containment checks
on scalar values, nested objects, and nested arrays.

```sql
-- GIN index
CREATE INDEX idx_products_attributes
    ON products USING GIN (attributes);

-- Scalar value match
SELECT name FROM products WHERE attributes @> '{"brand": "Dell"}';

-- Multi-key match (AND semantics)
SELECT name FROM products WHERE attributes @> '{"brand": "Apple", "price_range": "premium"}';

-- Array containment — "has feature: ssd"
SELECT name FROM products WHERE attributes @> '{"features": ["ssd"]}';

-- Key-existence operators (also GIN-accelerated)
SELECT name FROM products WHERE attributes ?  'subcategory';        -- key exists
SELECT name FROM products WHERE attributes ?| ARRAY['brand','sku']; -- any key
SELECT name FROM products WHERE attributes ?& ARRAY['brand','specs'];-- all keys
```

---

## Project layout

```
src/
  pgindexes/
    db.py              # psycopg2 connection + cursor helpers
    main.py            # demo orchestrator
    gin/
      schema.py        # CREATE TABLE + GIN indexes (DDL)
      seed.py          # sample articles and products
      fts.py           # full-text search demo (tsvector + @@)
      jsonb.py         # JSONB containment demo (@>)
```

---

## Prerequisites

Two tools are required: **Docker** (with the Compose plugin) and **uv** (Python package manager).

---

### Docker

Docker Desktop ships with the `docker compose` plugin included. Install it for your platform:

#### macOS

```bash
# Homebrew (recommended)
brew install --cask docker

# Or download Docker Desktop from https://www.docker.com/products/docker-desktop/
```

After install, open **Docker Desktop** once to complete setup, then verify:

```bash
docker --version
docker compose version
```

#### Linux

```bash
# Official convenience script (Ubuntu / Debian / Fedora / RHEL)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # add yourself to the docker group
newgrp docker                   # apply without logging out

# Verify
docker --version
docker compose version
```

> For other distros see the [official install docs](https://docs.docker.com/engine/install/).

#### Windows

```powershell
# WinGet
winget install Docker.DockerDesktop

# Or download the installer from https://www.docker.com/products/docker-desktop/
```

After install, open **Docker Desktop** once to complete setup.

---

### uv (Python package manager)

#### macOS / Linux

```bash
# Official installer (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or via Homebrew
brew install uv

# Or via asdf
asdf plugin add uv
asdf install uv latest
asdf global uv latest
```

#### Windows

```powershell
# WinGet
winget install astral-sh.uv

# Or via the official installer
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verify:

```bash
uv --version
```

---

## Project setup

```bash
# 1. Clone the repo
git clone <repo-url>
cd pgindexes

# 2. Copy env file and adjust credentials if needed
cp .env.example .env

# 3. Install Python dependencies
uv sync

# 4. Start the Postgres backend
docker compose up -d
```

See [DOCKER.md](DOCKER.md) for more Docker-specific details.

---

## Running the demos

```bash
# Run all demos (schema setup + seed + FTS + JSONB)
uv run pgindexes

# Or equivalently
uv run python -m pgindexes
```

The script will:
1. Drop and recreate the demo tables with GIN indexes.
2. Seed 10 articles and 10 products.
3. Run the full-text search demo, printing matched titles, ranks, and headlines.
4. Run the JSONB demo, printing containment and key-existence query results.
5. Print `EXPLAIN` output for each demo to confirm the GIN index is hit.
