"""Read committed V3 context in a fresh process."""

from __future__ import annotations

import argparse
import base64
import json
import sqlite3


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--keys", nargs="+", required=True)
    args = parser.parse_args()
    conn = sqlite3.connect(f"file:{args.database}?mode=ro", uri=True)
    try:
        values = {}
        for key in args.keys:
            row = conn.execute(
                "SELECT payload FROM context_values "
                "WHERE workflow_id = ? AND key = ? AND committed = 1",
                (args.workflow, key),
            ).fetchone()
            if row is None:
                raise SystemExit(f"missing committed key: {key}")
            values[key] = base64.b64encode(row[0]).decode("ascii")
    finally:
        conn.close()
    print(json.dumps(values, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
