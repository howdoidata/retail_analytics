"""Synthetic source-data generator (story C-4).

`generate(out_dir, seed)` writes the six source CSVs described in `docs/data-contracts.md`,
deterministic from the seed (default 42): a clean simulated population (`simulate.py`) with the
deliberate mess M1-M6 layered on top (`mess.py`). Formats and shares: `data/raw/README.md`.
"""

from __future__ import annotations

import random
from pathlib import Path

from retail_analytics.generator import mess, simulate

DEFAULT_SEED = 42

# Contract file names and column order (docs/data-contracts.md, "Source CSVs").
COLUMNS = {
    "customers": [
        "id", "created_at", "email", "first_name", "last_name", "state", "signup_location",
        "accepts_marketing",
    ],
    "orders": [
        "id", "customer_id", "created_at", "sales_channel", "status", "subtotal", "discount", "total",
        "currency",
    ],
    "order_lines": ["id", "order_id", "product_id", "quantity", "unit_price"],
    "products": ["id", "title", "category", "list_price"],
    "marketing_touches": [
        "id", "customer_email", "touched_at", "channel", "campaign", "utm_source", "utm_medium",
        "utm_campaign",
    ],
    "ad_spend": ["date", "channel", "campaign", "spend"],
}  # fmt: skip


def _field(value: str) -> str:
    """Quote a value only when needed: a delimiter, quote, line break, or surrounding whitespace."""
    if any(ch in value for ch in ',"\r\n') or value != value.strip():
        return '"' + value.replace('"', '""') + '"'
    return value


def _write(path: Path, header: list[str], rows: list[list[str]]) -> None:
    lines = [",".join(_field(v) for v in row) for row in [header, *rows]]
    path.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))


def generate(out_dir: Path, seed: int = DEFAULT_SEED) -> dict[str, int]:
    """Write the six CSVs to `out_dir` (created if missing, files overwritten).

    Returns how many rows of each mess item were injected.
    """
    rng = random.Random(seed)
    tables = mess.apply(rng, simulate.simulate(rng))
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, header in COLUMNS.items():
        _write(out_dir / f"{name}.csv", header, getattr(tables, name))
    return tables.report
