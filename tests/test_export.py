"""Checks for the C-13 export (`uv run export`): the cell formatter rounds as the contract says (values the
mart types cannot hold); a DuckDB file built here with the marts' column types exports byte for byte to
`tests/fixtures/export/`, the same on a rerun; a missing database, mart, or column exits 1 naming it and
writes nothing; each mart's columns, unique key, and rounding are the ones in `docs/data-contracts.md`; and
on seed 42 the export's headers, row counts, and cells match the marts."""

from __future__ import annotations

import csv
import importlib
import re
import shutil
import tomllib
from datetime import date, datetime
from decimal import Decimal
from itertools import dropwhile, takewhile
from pathlib import Path

import duckdb
import pytest
from test_cohorts_mart import CONTRACT_COLUMNS as COHORTS_COLUMNS
from test_funnel_mart import CONTRACT_COLUMNS as FUNNEL_COLUMNS
from test_signups_mart import CONTRACT_COLUMNS as SIGNUPS_COLUMNS
from test_staging import dbt_build, failed, rows

from retail_analytics import config, export
from retail_analytics.config import DBT_DIR, DOCS_DIR, REPO_ROOT
from retail_analytics.generator import generate

CONTRACT = DOCS_DIR / "data-contracts.md"
EXPECTED = Path(__file__).resolve().parent / "fixtures" / "export"
D = Decimal
Q1, Q2 = date(2024, 1, 1), date(2024, 4, 1)
JAN, FEB = date(2024, 1, 1), date(2024, 2, 1)

# The marts' column types (the mart tests pin them against the built models).
MART_TYPES = {
    "fct_signups_by_channel": SIGNUPS_COLUMNS,
    "fct_visit_funnel_by_channel": FUNNEL_COLUMNS,
    "fct_customer_cohorts": COHORTS_COLUMNS,
}
# Fixture rows in contract column order, deliberately not in unique-key order. Covered: nulls (first-quarter
# prior and change, the funnel signup row), zero as 0, trailing zeros dropped, large values without
# scientific notation, a text cell with a comma (quoted), milestone 10 sorting after 5.
ROWS = {
    "fct_signups_by_channel": [
        ("Paid Social", Q2, 1, 2, D("-0.500000"), D("0.166667"), D("50.00"), D("50.00"), True),
        ("Referral, partner sites", Q2, 2, 0, None, D("0.333333"), D("0.00"), None, True),
        ("Email", Q1, 2, None, None, D("0.500000"), D("0.00"), None, True),
        ("Paid Social", Q1, 2, None, None, D("0.500000"), D("1234567.80"), D("617283.90"), True),
        ("Email", Q2, 3, 2, D("0.500000"), D("0.500000"), D("12.35"), D("4.12"), True),
        ("Referral, partner sites", Q1, 0, None, None, D("0.000000"), D("0.00"), None, True),
    ],
    "fct_visit_funnel_by_channel": [
        ("Paid Search", FEB, 0, None, 0, None, None, D("0.00"), True),
        ("Paid Search", JAN, 10, 5, 0, D("0.000000"), None, None, True),
        ("Paid Search", JAN, 2, 1, 6, D("0.750000"), D("14.33"), None, True),
        ("Email", JAN, 1, 0, 3, D("1.000000"), D("0.00"), None, True),
        ("Paid Search", JAN, 0, None, 10, None, None, D("1234.50"), True),
        ("Paid Search", JAN, 5, 3, 1, D("0.250000"), D("61.25"), None, True),
        ("Paid Search", JAN, 1, 0, 8, D("0.800000"), D("2.50"), None, True),
        ("Email", JAN, 0, None, 3, None, None, D("0.00"), True),
        ("Paid Search", JAN, 3, 2, 4, D("0.666667"), D("30.00"), None, True),
    ],
    "fct_customer_cohorts": [
        ("Paid Social", Q2, 0, 2, 2, D("1.000000"), 2, D("1.0000"), D("80.10"), D("40.05"), True),
        ("Paid Social", Q1, 2, 4, 0, D("0.000000"), 0, None, D("0.00"), None, True),
        ("Paid Social", Q1, 0, 4, 3, D("0.750000"), 5, D("1.6667"), D("312.40"), D("62.48"), True),
        ("Email", Q2, 0, 3, 3, D("1.000000"), 4, D("1.3333"), D("1234567.89"), D("308641.97"), True),
        ("Paid Social", Q1, 1, 4, 1, D("0.250000"), 1, D("1.0000"), D("100.00"), D("100.00"), True),
    ],
}


def fixture_db(path: Path, shuffled: bool = False) -> Path:
    """The fixture marts in a new DuckDB file at `path`, in schema `main` with the marts' column types.
    `shuffled` reverses each table's columns and adds one the contract does not have."""
    with duckdb.connect(str(path)) as con:
        for mart, columns in MART_TYPES.items():
            table = [*reversed(columns), ("loaded_note", "VARCHAR")] if shuffled else columns
            names = [name for name, _ in columns]
            con.execute(f"create table main.{mart} ({', '.join(f'{n} {t}' for n, t in table)})")
            con.executemany(
                f"insert into main.{mart} ({', '.join(names)}) values ({', '.join('?' * len(names))})",
                ROWS[mart],
            )
    return path


def run_export(database: Path | None, out: Path) -> dict[str, bytes]:
    """`uv run export` into `out` (with `--database` unless None); every file in `out` by name."""
    export.main(["--output-dir", str(out)] + (["--database", str(database)] if database else []))
    return {p.name: p.read_bytes() for p in sorted(out.iterdir())}


def export_fails(database: Path | None, out: Path, capsys: pytest.CaptureFixture[str]) -> str:
    """Export into `out` (with `--database` unless None) exits 1, writes nothing, and says so; returns
    stderr."""
    with pytest.raises(SystemExit) as stopped:
        export.main(["--output-dir", str(out)] + (["--database", str(database)] if database else []))
    assert stopped.value.code == 1
    assert not out.exists() or not any(out.iterdir())
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "nothing was written" in captured.err
    return captured.err


def expected_files() -> dict[str, bytes]:
    return {f"{mart}.csv": (EXPECTED / f"{mart}.csv").read_bytes() for mart in export.MARTS}


# ---- cells --------------------------------------------------------------------------------------

ROUNDING = [
    # The story's I/O matrix.
    (D("0.5000005"), 6, "0.500001"),
    (D("2.345"), 2, "2.35"),
    (D("0.500000"), 6, "0.5"),
    (D("100.00"), 2, "100"),
    (D("0.000001"), 6, "0.000001"),
    (D("-0.0000001"), 6, "0"),
    (1.005, 2, "1.01"),
    # Half away from zero on the negative side, a float negative zero, values in exponent form.
    (D("-2.345"), 2, "-2.35"),
    (-0.0, 2, "0"),
    (D("1E-7"), 6, "0"),
    (D("1E+7"), 2, "10000000"),
]


@pytest.mark.parametrize(("value", "digits", "text"), ROUNDING, ids=[f"{v}@{d}" for v, d, _ in ROUNDING])
def test_decimal_cell_rounding(value: Decimal | float, digits: int, text: str) -> None:
    assert export.cell(value, f"decimal({digits})") == text


@pytest.mark.parametrize(
    ("value", "fmt"),
    [(datetime(2024, 1, 1), "date"), ("2024-01-01", "date"), (True, "int"), (1, "boolean"), (1, "text")],
)
def test_cell_rejects_a_value_that_does_not_fit(value: object, fmt: str) -> None:
    with pytest.raises(TypeError):
        export.cell(value, fmt)


def test_cell_boolean_false() -> None:
    assert export.cell(False, "boolean") == "false"


def test_render_quotes_and_encodes_text() -> None:
    """A text value with double quotes and a non-ASCII character: quoted, quotes doubled, UTF-8, no BOM."""
    row = ('Café "Trail" Co', Q1, 1, None, None, D("1.000000"), D("0.00"), None, True)
    header, line = export.render("fct_signups_by_channel", [row]).split(b"\n", 1)
    assert header.startswith(b"channel,quarter,")
    assert line == b'"Caf\xc3\xa9 ""Trail"" Co",2024-01-01,1,,,1,0,,true\n'


# ---- the fixture database -----------------------------------------------------------------------


def test_fixture_database_exports_the_expected_bytes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Happy path, nulls, quoting, and rounding of stored values; the rerun leaves identical bytes; success
    prints each file with its row count."""
    database = fixture_db(tmp_path / "marts.duckdb")
    out = tmp_path / "new" / "export"  # created if missing
    assert run_export(database, out) == expected_files()
    printed = capsys.readouterr().out.splitlines()
    assert printed == [
        f"wrote {export._shown(out / f'{mart}.csv')} ({len(ROWS[mart])} rows)" for mart in export.MARTS
    ]
    assert run_export(database, out) == expected_files()


def test_columns_are_selected_by_name(tmp_path: Path) -> None:
    """A mart whose columns are in another order, with one more column, exports the same bytes."""
    database = fixture_db(tmp_path / "marts.duckdb", shuffled=True)
    assert run_export(database, tmp_path / "export") == expected_files()


def test_database_defaults_to_the_build_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without `--database`: `$RETAIL_DUCKDB_PATH` if set, else the profile's default; a relative path
    resolves from the repo root."""
    profile = (DBT_DIR / "profiles.yml").read_text(encoding="utf-8")
    assert f"env_var('{export.DATABASE_ENV}', '{export.DEFAULT_DATABASE.as_posix()}')" in profile

    monkeypatch.setenv(export.DATABASE_ENV, str(fixture_db(tmp_path / "marts.duckdb")))
    assert run_export(None, tmp_path / "export") == expected_files()
    capsys.readouterr()

    monkeypatch.setenv(export.DATABASE_ENV, "no-such-dir/marts.duckdb")
    err = export_fails(None, tmp_path / "unused", capsys)
    assert str(REPO_ROOT / "no-such-dir" / "marts.duckdb") in err
    assert export.BUILD_HINT in err


def test_no_flags_read_the_default_database_into_data_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No `--database`, no `$RETAIL_DUCKDB_PATH`, no `--output-dir`: `data/retail_analytics.duckdb` is
    exported to `data/export/`, both under the repo root (here a stand-in)."""
    assert config.EXPORT_DIR == config.REPO_ROOT / "data" / "export"
    monkeypatch.delenv(export.DATABASE_ENV, raising=False)
    monkeypatch.setattr(export, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(export, "EXPORT_DIR", tmp_path / "data" / "export")
    (tmp_path / "data").mkdir()
    fixture_db(tmp_path / "data" / "retail_analytics.duckdb")
    export.main([])
    out = tmp_path / "data" / "export"
    assert {p.name: p.read_bytes() for p in sorted(out.iterdir())} == expected_files()


def test_export_script_entry() -> None:
    """`[project.scripts] export` resolves to this module's `main`."""
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    module, _, attribute = pyproject["project"]["scripts"]["export"].partition(":")
    assert getattr(importlib.import_module(module), attribute) is export.main


def test_no_database(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = tmp_path / "absent.duckdb"
    err = export_fails(missing, tmp_path / "export", capsys)
    assert str(missing) in err
    assert export.BUILD_HINT in err


def test_database_that_cannot_be_opened(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    junk = tmp_path / "junk.duckdb"
    junk.write_bytes(b"not a DuckDB file\n" * 512)
    err = export_fails(junk, tmp_path / "export", capsys)
    assert f"cannot open database {junk}" in err
    assert export.LOCKED_HINT in err
    assert export.BUILD_HINT not in err


def test_missing_mart(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    database = fixture_db(tmp_path / "marts.duckdb")
    with duckdb.connect(str(database)) as con:
        con.execute("drop table main.fct_customer_cohorts")
    err = export_fails(database, tmp_path / "export", capsys)
    assert "main.fct_customer_cohorts" in err
    assert export.BUILD_HINT in err


def test_missing_column(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    database = fixture_db(tmp_path / "marts.duckdb")
    with duckdb.connect(str(database)) as con:
        con.execute("alter table main.fct_signups_by_channel drop column ad_spend")
    err = export_fails(database, tmp_path / "export", capsys)
    assert "fct_signups_by_channel.ad_spend" in err
    assert "fct_visit_funnel_by_channel.ad_spend" not in err
    assert export.BUILD_HINT in err


def test_every_missing_mart_and_column_is_named(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    database = fixture_db(tmp_path / "marts.duckdb")
    with duckdb.connect(str(database)) as con:
        con.execute("drop table main.fct_customer_cohorts")
        con.execute("alter table main.fct_signups_by_channel drop column ad_spend")
    err = export_fails(database, tmp_path / "export", capsys)
    assert "main.fct_customer_cohorts" in err
    assert "fct_signups_by_channel.ad_spend" in err


def test_value_that_no_longer_fits_its_format(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A date column turned timestamp would export as `2024-01-01 00:00:00`; it fails instead."""
    database = fixture_db(tmp_path / "marts.duckdb")
    with duckdb.connect(str(database)) as con:
        con.execute("alter table main.fct_signups_by_channel alter quarter type timestamp")
    err = export_fails(database, tmp_path / "export", capsys)
    assert "fct_signups_by_channel.quarter" in err
    assert export.FORMAT_HINT in err
    assert export.BUILD_HINT not in err


# ---- the contract -------------------------------------------------------------------------------


def contract_table(mart: str) -> list[tuple[str, str]]:
    """(column, type) of each row of the mart's table in the contract, in order."""
    lines = CONTRACT.read_text(encoding="utf-8").splitlines()
    after = lines[next(i for i, line in enumerate(lines) if line.startswith(f"`{mart}`.")) + 1 :]

    def is_row(line: str) -> bool:
        return line.startswith("|")

    table = list(takewhile(is_row, dropwhile(lambda line: not is_row(line), after)))
    return [tuple(c.strip() for c in row.strip("|").split("|")[:2]) for row in table[2:]]


def contract_key(mart: str) -> tuple[str, ...]:
    match = re.search(rf"^`{mart}`\. Unique key \(([^)]+)\)", CONTRACT.read_text(encoding="utf-8"), re.M)
    assert match, mart
    return tuple(name.strip() for name in match[1].split(","))


def contract_rounding() -> dict[str, int]:
    """Column -> decimal digits from the Exports section's rounding line."""
    text = CONTRACT.read_text(encoding="utf-8")
    line = next(line for line in text.splitlines() if line.startswith("- Rounding"))
    digits: dict[str, int] = {}
    for part in line.split(";"):
        places = int(re.findall(r"\d+", part)[-1])
        digits.update((name, places) for name in re.findall(r"`(\w+)`", part))
    return digits


@pytest.mark.parametrize("mart", export.MARTS)
def test_header_and_formats_follow_the_contract(mart: str) -> None:
    """The header is the column order of the mart's table in the contract, each format is that column's
    type, and the rows are ordered by the contract's unique key."""
    spec = export.MARTS[mart]
    table = contract_table(mart)
    header = (EXPECTED / f"{mart}.csv").read_text(encoding="utf-8").splitlines()[0].split(",")
    assert header == [name for name, _ in table]
    assert [name for name, _ in spec.columns] == [name for name, _ in table]
    assert [fmt.split("(")[0] for _, fmt in spec.columns] == [kind for _, kind in table]
    assert spec.key == contract_key(mart)


def test_rounding_follows_the_contract() -> None:
    """Every decimal column has the digits the contract's Exports section gives it, and every column named
    there is a decimal column."""
    rounding = contract_rounding()
    decimals = {
        name: int(fmt[len("decimal(") : -1])
        for spec in export.MARTS.values()
        for name, fmt in spec.columns
        if fmt.startswith("decimal(")
    }
    assert decimals == rounding


# ---- seed 42 ------------------------------------------------------------------------------------


def parse(text: str, fmt: str) -> object:
    """A cell back to its value, checking its form: null is empty; dates ISO; booleans true/false; decimals
    plain, at most `digits` places, no trailing zeros, never `-0`."""
    if text == "":
        return None
    if fmt == "text":
        return text
    if fmt == "date":
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", text), text
        return date.fromisoformat(text)
    if fmt == "int":
        assert re.fullmatch(r"-?\d+", text), text
        return int(text)
    if fmt == "boolean":
        assert text in ("true", "false"), text
        return text == "true"
    digits = int(fmt[len("decimal(") : -1])
    assert re.fullmatch(rf"-?\d+(\.\d{{0,{digits - 1}}}[1-9])?", text) and text != "-0", text
    return Decimal(text)


def test_seed_42_end_to_end(tmp_path: Path) -> None:
    """Generate, dbt build, export: each header is the contract's, the row count is the mart's, every cell
    parses back to the mart's value (the marts store the export's digits), and a rerun gives the same bytes;
    prints the row counts (`pytest -s`). dbt keeps its read-write connection open in this process (`uv run
    build` would have exited), so the export reads a checkpointed byte copy of the warehouse."""
    raw = tmp_path / "raw"
    generate(raw, 42)
    result = dbt_build(raw, tmp_path)
    assert result.success, failed(result)
    with duckdb.connect(str(tmp_path / "warehouse.duckdb")) as con:
        con.execute("checkpoint")
    database, out = tmp_path / "built.duckdb", tmp_path / "export"
    shutil.copyfile(tmp_path / "warehouse.duckdb", database)
    first = run_export(database, out)
    assert sorted(first) == sorted(f"{mart}.csv" for mart in export.MARTS)
    assert run_export(database, out) == first

    counts = {}
    for mart, spec in export.MARTS.items():
        with (out / f"{mart}.csv").open(newline="", encoding="utf-8") as f:
            header, *records = list(csv.reader(f))
        assert header == [name for name, _ in contract_table(mart)]
        [(count,)] = rows(tmp_path, f"select count(*) from main.{mart}")
        assert len(records) == count > 0
        parsed = [tuple(parse(c, fmt) for c, (_, fmt) in zip(r, spec.columns, strict=True)) for r in records]
        assert parsed == rows(tmp_path, f"select * from main.{mart} order by {', '.join(spec.key)}")
        counts[mart] = count
    print("\nSeed-42 export rows: " + ", ".join(f"{mart} {n}" for mart, n in counts.items()))
