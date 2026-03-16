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

## To run all the demos 

```bash
# Run all demos (schema setup + seed + FTS + JSONB)
uv run pgindexes

# Run only the GIN demo
uv run pgindexes --demo gin

# Or equivalently
uv run python -m pgindexes --demo gin
```

---

## Convenience shell scripts for individual demos

The `scripts/` folder contains one-shot shell scripts that handle the full
lifecycle (start DB → run demo → optionally clean up) in a single command.
They work on **macOS, Linux (all distros), WSL, and Windows Git Bash**.

### `scripts/run_gin.sh` — GIN index experiment

```bash
# Start DB, run the GIN demo, leave the DB running afterwards
bash scripts/run_gin.sh

# Start DB, run the GIN demo, then stop & remove the DB container
bash scripts/run_gin.sh --clean

# Only stop & remove the DB container (no demo run)
bash scripts/run_gin.sh --down
```

What the script does automatically:

| Step | Detail |
|---|---|
| Detects OS / shell | macOS · Linux · WSL · Windows Git Bash |
| Checks dependencies | `docker`, `docker compose` / `docker-compose`, `uv` (falls back to `python3`) |
| Starts the DB | `docker compose up -d db` |
| Waits for ready | Polls `pg_isready` (up to 60 s) before proceeding |
| Runs the demo | `uv run pgindexes` (or `python3 -m pgindexes` if uv is absent) |
| Cleans up | Only when `--clean` is passed — otherwise the container keeps running |

> **Adding more experiments:** Future scripts follow the same naming pattern —
> `scripts/run_brin.sh`, `scripts/run_hash.sh`, `scripts/run_btree.sh`, etc.
> Each script is self-contained so you can run any single experiment in isolation.
