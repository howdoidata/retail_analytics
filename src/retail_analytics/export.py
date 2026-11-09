"""`uv run export`: write the three marts to `data/export/<mart>.csv` for the dashboard.

Reads `main.<mart>` from the DuckDB file `uv run build` writes, opened read-only; dbt is never run.

The contract ("Exports" in `docs/data-contracts.md`) sets: UTF-8, comma-delimited, a header row, columns in
contract order, dates `YYYY-MM-DD`, booleans `true`/`false`, null as an empty cell, and decimals rounded (not
zero-padded) to each column's digits. This command adds: no BOM, LF line ends, minimal quoting; rounding half
away from zero, trailing zeros dropped, no scientific notation, zero as `0`; rows ordered by the mart's
unique key, then its other columns, so the same database always gives byte-identical files.

All three marts are read and rendered before any file is written. A missing database, mart, or column, a
database that cannot be opened, or a value that no longer fits its column's format is named on stderr with
exit 1, and nothing is written. `--database PATH` defaults to `$RETAIL_DUCKDB_PATH` if set, else
`data/retail_analytics.duckdb`, as in the dbt profile; relative paths (here and for `--output-dir`) resolve
from the repo root, as the build's do.
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import re
import sys
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import NamedTuple

import duckdb

from retail_analytics.config import EXPORT_DIR, REPO_ROOT

DATABASE_ENV = "RETAIL_DUCKDB_PATH"
DEFAULT_DATABASE = Path("data") / "retail_analytics.duckdb"
SCHEMA = "main"
BUILD_HINT = "run `uv run build` first"
LOCKED_HINT = "another process (a running build or a DuckDB session) may be holding it"
FORMAT_HINT = "the mart's column type no longer matches the export's format"


class Mart(NamedTuple):
    key: tuple[str, ...]
    columns: tuple[tuple[str, str], ...]


# Each mart's unique key and its columns in contract order, with the cell format: text, date, int,
# boolean, or decimal(digits) (docs/data-contracts.md, the mart tables and "Exports").
MARTS = {
    "fct_signups_by_channel": Mart(
        key=("channel", "quarter"),
        columns=(
            ("channel", "text"),
            ("quarter", "date"),
            ("signups", "int"),
            ("signups_prior_quarter", "int"),
            ("signups_change", "decimal(6)"),
            ("share_of_signups", "decimal(6)"),
            ("ad_spend", "decimal(2)"),
            ("cost_per_signup", "decimal(2)"),
            ("is_simulated", "boolean"),
        ),
    ),
    "fct_visit_funnel_by_channel": Mart(
        key=("channel", "cohort_month", "milestone"),
        columns=(
            ("channel", "text"),
            ("cohort_month", "date"),
            ("milestone", "int"),
            ("previous_milestone", "int"),
            ("customers_reached", "int"),
            ("step_rate", "decimal(6)"),
            ("avg_days_from_previous", "decimal(2)"),
            ("ad_spend", "decimal(2)"),
            ("is_simulated", "boolean"),
        ),
    ),
    "fct_customer_cohorts": Mart(
        key=("channel", "cohort_quarter", "quarters_since_signup"),
        columns=(
            ("channel", "text"),
            ("cohort_quarter", "date"),
            ("quarters_since_signup", "int"),
            ("cohort_size", "int"),
            ("active_customers", "int"),
            ("active_rate", "decimal(6)"),
            ("visits", "int"),
            ("visits_per_active_customer", "decimal(4)"),
            ("revenue", "decimal(2)"),
            ("average_order", "decimal(2)"),
            ("is_simulated", "boolean"),
        ),
    ),
}

_DECIMAL = re.compile(r"decimal\((\d+)\)")


class ExportError(Exception):
    """Why the export cannot run: one line per missing database, mart, or column, unopenable database, or
    misfit value, and the hint for what to do."""

    def __init__(self, problems: list[str], hint: str) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems
        self.hint = hint


# ---- cells --------------------------------------------------------------------------------------


def decimal_cell(value: Decimal | float | int, digits: int) -> str:
    """`value` rounded half away from zero to `digits` places, trailing zeros (then a bare `.`) dropped,
    never in scientific notation; zero, including a negative value that rounds to zero, is `0`. A float goes
    through `str` first, so `1.005` rounds as written, not as its binary expansion."""
    rounded = Decimal(str(value)).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)
    if rounded == 0:
        return "0"
    text = format(rounded, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def cell(value: object, fmt: str) -> str:
    """One cell's text for `value` in format `fmt` (text, date, int, boolean, or decimal(digits)), before CSV
    quoting: null is empty. Raises `TypeError` when the value does not fit the format."""
    if value is None:
        return ""
    if fmt == "text" and isinstance(value, str):
        return value
    if fmt == "date" and isinstance(value, date) and not isinstance(value, datetime):
        return value.isoformat()
    if fmt == "int" and isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if fmt == "boolean" and isinstance(value, bool):
        return "true" if value else "false"
    decimal = _DECIMAL.fullmatch(fmt)
    if decimal and isinstance(value, Decimal | float | int) and not isinstance(value, bool):
        return decimal_cell(value, int(decimal[1]))
    raise TypeError(f"cannot format {value!r} as {fmt}")


def render(mart: str, rows: list[tuple]) -> bytes:
    """The CSV file for `mart`: header row, then one line per row (values in contract column order)."""
    columns = MARTS[mart].columns
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")  # minimal quoting
    writer.writerow([name for name, _ in columns])
    for row in rows:
        cells = []
        for value, (column, fmt) in zip(row, columns, strict=True):
            try:
                cells.append(cell(value, fmt))
            except TypeError as error:
                raise ExportError([f"{mart}.{column}: {error}"], FORMAT_HINT) from None
        writer.writerow(cells)
    return out.getvalue().encode("utf-8")


# ---- reading ------------------------------------------------------------------------------------


def _quoted(names: tuple[str, ...] | list[str]) -> str:
    return ", ".join(f'"{name}"' for name in names)


def select_sql(mart: str) -> str:
    """The contract columns of `main.<mart>`, selected by name, ordered by the unique key and then the other
    columns (a total order even if a failed dbt test left duplicate keys in the mart)."""
    spec = MARTS[mart]
    names = [name for name, _ in spec.columns]
    order = [*spec.key, *(name for name in names if name not in spec.key)]
    return f'select {_quoted(names)} from {SCHEMA}."{mart}" order by {_quoted(order)}'


def read_marts(database: Path) -> dict[str, list[tuple]]:
    """Every mart's rows from `database`, opened read-only. Raises `ExportError` naming the database if it
    is missing or cannot be opened, else every missing mart and `mart.column`."""
    if not database.is_file():
        raise ExportError([f"database not found: {database}"], BUILD_HINT)
    try:
        con = duckdb.connect(str(database), read_only=True)
    except duckdb.Error as error:
        raise ExportError([f"cannot open database {database}: {error}"], LOCKED_HINT) from None
    with con:
        found: dict[str, set[str]] = {}
        for table, column in con.execute(
            "select table_name, column_name from information_schema.columns "
            "where table_catalog = current_database() and table_schema = ?",
            [SCHEMA],
        ).fetchall():
            found.setdefault(table, set()).add(column)
        problems: list[str] = []
        for mart, spec in MARTS.items():
            if mart not in found:
                problems.append(f"mart not found in {database}: {SCHEMA}.{mart}")
                continue
            problems += [
                f"column not found in {database}: {mart}.{name}"
                for name, _ in spec.columns
                if name not in found[mart]
            ]
        if problems:
            raise ExportError(problems, BUILD_HINT)
        return {mart: con.execute(select_sql(mart)).fetchall() for mart in MARTS}


# ---- command ------------------------------------------------------------------------------------


def _from_root(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def _shown(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT)) if path.is_relative_to(REPO_ROOT) else str(path)


def main(argv: list[str] | None = None) -> None:
    """Entry point for `uv run export [--database PATH] [--output-dir DIR]`."""
    parser = argparse.ArgumentParser(prog="export", description=__doc__.splitlines()[0])
    parser.add_argument(
        "--database",
        type=Path,
        metavar="PATH",
        help=f"DuckDB file to read (default: ${DATABASE_ENV} if set, else {DEFAULT_DATABASE}); "
        "relative paths resolve from the repo root",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        metavar="DIR",
        default=EXPORT_DIR,
        help="folder for the CSV files, created if missing (default: data/export/)",
    )
    args = parser.parse_args(argv)
    database = _from_root(args.database or Path(os.environ.get(DATABASE_ENV) or DEFAULT_DATABASE))
    output_dir = _from_root(args.output_dir)

    try:
        files = {mart: (render(mart, rows), len(rows)) for mart, rows in read_marts(database).items()}
    except ExportError as error:
        for problem in error.problems:
            print(f"export: {problem}", file=sys.stderr)
        print(f"export: {error.hint}; nothing was written", file=sys.stderr)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    for mart, (content, count) in files.items():
        path = output_dir / f"{mart}.csv"
        path.write_bytes(content)
        print(f"wrote {_shown(path)} ({count} rows)")


if __name__ == "__main__":  # `python -m retail_analytics.export`, how `uv run build` calls it
    main()
