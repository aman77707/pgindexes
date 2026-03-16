"""
Entry point for the pgindexes demos.

Run via:
    uv run pgindexes                # run all demos
    uv run pgindexes --demo gin     # run only the GIN demo
    uv run python -m pgindexes --demo gin

As new index types are added (brin, hash, btree …) pass --demo <name>
to run just that experiment in isolation.
"""

from __future__ import annotations

import argparse
import sys

from pgindexes.db import ensure_database, get_connection
from pgindexes.gin import fts, jsonb, schema, seed

# Registry: demo name → (setup_fn, [run_fns])
# Add a new entry here when a new index experiment is introduced.
_DEMOS: dict[str, dict] = {
    "gin": {
        "label": "GIN Index Demo",
        "setup": lambda conn: (schema.setup(conn), seed.seed(conn)),
        "run": [fts.run, jsonb.run],
    },
    # future entries, e.g.:
    # "brin": { "label": "BRIN Index Demo", "setup": ..., "run": [...] },
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="pgindexes",
        description="PostgreSQL index experiments.",
    )
    parser.add_argument(
        "--demo",
        metavar="NAME",
        choices=list(_DEMOS.keys()),
        default=None,
        help=(
            "Run only this demo. Choices: %(choices)s. "
            "Omit to run all demos."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    # Determine which demos to run
    if args.demo:
        demos_to_run = [args.demo]
    else:
        demos_to_run = list(_DEMOS.keys())

    ensure_database()
    conn = get_connection()
    try:
        print(
            "\n════════════════════════════════════════════════════════════════════════"
        )
        label = _DEMOS[demos_to_run[0]]["label"] if len(demos_to_run) == 1 else "pgindexes — All Demos"
        print(f"  {label}")
        print(
            "════════════════════════════════════════════════════════════════════════\n"
        )

        for name in demos_to_run:
            demo = _DEMOS[name]
            # setup (schema + seed) for this demo
            demo["setup"](conn)
            # run each demo function
            for fn in demo["run"]:
                fn(conn)

        print(
            "════════════════════════════════════════════════════════════════════════"
        )
        print("  Demo complete.")
        print(
            "════════════════════════════════════════════════════════════════════════\n"
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
