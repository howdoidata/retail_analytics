"""Checks for the C-7 sign-ups mart (`fct_signups_by_channel`): built on hand-made fixtures shaped like
`dim_customers` and `int_channel_spend_daily` (`tests/fixtures/intermediate/`) loaded into an
`intermediate` schema, each case of the story's I/O matrix gives the expected row, a broken fixture fails
its dbt test, the columns are the contract's in order, every column is described, and on seed 42 every dbt
test passes with 7 channels x 8 quarters."""

from __future__ import annotations

import json
import shutil
from datetime import date
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest
from dbt.cli.main import dbtRunnerResult
from test_staging import FIXTURES as RAW_FIXTURES
from test_staging import dbt_build, failed, rows

from retail_analytics.config import DBT_DIR
from retail_analytics.generator import generate

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "intermediate"
MART = "main.fct_signups_by_channel"
CONTRACT_COLUMNS = [
    ("channel", "VARCHAR"),
    ("quarter", "DATE"),
    ("signups", "INTEGER"),
    ("signups_prior_quarter", "INTEGER"),
    ("signups_change", "DECIMAL(18,6)"),
    ("share_of_signups", "DECIMAL(18,6)"),
    ("ad_spend", "DECIMAL(18,2)"),
    ("cost_per_signup", "DECIMAL(18,2)"),
    ("is_simulated", "BOOLEAN"),
]
# Column types of the intermediate models the mart reads, in model column order. The dim_customers fixture
# leaves out `milestone_dates` (the mart does not read it); the loader adds it as an empty map column.
INTERMEDIATE_TYPES = {
    "dim_customers": {
        "customer_id": "bigint",
        "signup_date": "date",
        "signup_location": "varchar",
        "acquisition_channel": "varchar",
    },
    "int_channel_spend_daily": {
        "channel": "varchar",
        "spend_date": "date",
        "ad_spend": "decimal(18, 2)",
    },
}


def mart_build(intermediate_dir: Path, work: Path) -> dbtRunnerResult:
    """Load the intermediate fixtures into `intermediate` and the `channels` seed into `staging` of
    `work/warehouse.duckdb`, run the spend model's tests on its fixture, then `dbt build --select marts`.
    Returns the first failing result, else the mart build's."""
    with duckdb.connect(str(work / "warehouse.duckdb")) as con:
        con.execute("create schema intermediate")
        con.execute("create schema staging")
        for table, types in INTERMEDIATE_TYPES.items():
            columns = ", ".join(f"'{name}': '{kind}'" for name, kind in types.items())
            con.execute(
                f"create table intermediate.{table} as select * from read_csv("
                f"'{intermediate_dir / f'{table}.csv'}', header = true, columns = {{{columns}}})"
            )
        con.execute("alter table intermediate.dim_customers add column milestone_dates map(integer, date)")
        con.execute(
            f"create table staging.channels as select * from read_csv("
            f"'{DBT_DIR / 'seeds' / 'channels.csv'}', header = true, columns = {{'channel': 'varchar'}})"
        )
    # The spend total check compares against stg_ad_spend, which has no fixture here.
    spend_tests = dbt_build(
        RAW_FIXTURES,
        work,
        select=("int_channel_spend_daily,test_type:generic",),
        command="test",
    )
    if not spend_tests.success:
        return spend_tests
    return dbt_build(RAW_FIXTURES, work, select=("marts",))


@pytest.fixture(scope="module")
def fixture_build(tmp_path_factory: pytest.TempPathFactory) -> Path:
    work = tmp_path_factory.mktemp("mart_fixtures")
    result = mart_build(FIXTURES, work)
    assert result.success, failed(result)
    return work


def test_columns_follow_the_contract(fixture_build: Path) -> None:
    assert (
        rows(
            fixture_build,
            "select column_name, data_type from information_schema.columns "
            "where table_schema = 'main' and table_name = 'fct_signups_by_channel' order by ordinal_position",
        )
        == CONTRACT_COLUMNS
    )


def d(value: str | None) -> Decimal | None:
    return None if value is None else Decimal(value)


Q1, Q2, Q3, Q4 = date(2024, 1, 1), date(2024, 4, 1), date(2024, 7, 1), date(2024, 10, 1)
# (channel, quarter, signups, prior, change, share, ad_spend, cost_per_signup); is_simulated always true.
EXPECTED = [
    ("Direct/Unknown", Q1, 0, None, None, "0", "0.00", None),
    ("Direct/Unknown", Q2, 0, 0, None, "0", "0.00", None),
    ("Direct/Unknown", Q3, 0, 0, None, None, "0.00", None),
    ("Direct/Unknown", Q4, 2, 0, None, "0.333333", "0.00", None),
    ("Email", Q1, 1, None, None, "0.25", "0.00", None),
    ("Email", Q2, 2, 1, "1", "0.333333", "0.00", None),
    ("Email", Q3, 0, 2, "-1", None, "0.00", None),
    ("Email", Q4, 0, 0, None, "0", "0.00", None),
    ("In-store", Q1, 0, None, None, "0", "0.00", None),
    ("In-store", Q2, 0, 0, None, "0", "0.00", None),
    ("In-store", Q3, 0, 0, None, None, "0.00", None),
    ("In-store", Q4, 1, 0, None, "0.166667", "0.00", None),
    ("Organic Search", Q1, 0, None, None, "0", "0.00", None),
    ("Organic Search", Q2, 3, 0, None, "0.5", "0.00", None),
    ("Organic Search", Q3, 0, 3, "-1", None, "0.00", None),
    ("Organic Search", Q4, 0, 0, None, "0", "0.00", None),
    ("Paid Search", Q1, 0, None, None, "0", "100.00", None),
    ("Paid Search", Q2, 0, 0, None, "0", "0.00", None),
    ("Paid Search", Q3, 0, 0, None, None, "0.00", None),
    ("Paid Search", Q4, 3, 0, None, "0.5", "100.00", "33.33"),
    ("Paid Social", Q1, 2, None, None, "0.5", "300.00", "150.00"),
    ("Paid Social", Q2, 1, 2, "-0.5", "0.166667", "50.00", "50.00"),
    ("Paid Social", Q3, 0, 1, "-1", None, "0.00", None),
    ("Paid Social", Q4, 0, 0, None, "0", "0.00", None),
    ("Referral", Q1, 1, None, None, "0.25", "0.00", None),
    ("Referral", Q2, 0, 1, "-1", "0", "0.00", None),
    ("Referral", Q3, 0, 0, None, None, "0.00", None),
    ("Referral", Q4, 0, 0, None, "0", "0.00", None),
]


def test_every_row(fixture_build: Path) -> None:
    """The whole 7 x 4 grid. I/O matrix: Paid Social Q1, 2 sign-ups (10 Jan and 31 Mar) for $300, cost
    150.00; Referral Q2, no customers, so 0 sign-ups, share 0, cost null; Paid Search Q1, $100 spend and no
    sign-ups, cost null; Email, sign-ups with no spend, ad_spend 0.00 and cost null; Q1 is the first
    quarter, so prior and change are null; Organic Search Q2, prior 0 and 3 now, change null; Q3 has no
    sign-ups or spend, so every channel is 0 with share null; the sign-up on 1 Apr is Q2 (Paid Social)."""
    expected = [(ch, q, s, p, d(c), d(sh), d(sp), d(cps), True) for ch, q, s, p, c, sh, sp, cps in EXPECTED]
    assert rows(fixture_build, f"select * from {MART} order by channel, quarter") == expected


def test_signups_and_spend_totals(fixture_build: Path) -> None:
    assert rows(fixture_build, f"select sum(signups), sum(ad_spend) from {MART}") == [(16, Decimal("550.00"))]


def test_every_mart_node_is_described(fixture_build: Path) -> None:
    """The mart and every column have a description, the documented columns are the contract's in order,
    and the shared terms come from doc blocks."""
    manifest = json.loads((fixture_build / "target" / "manifest.json").read_text(encoding="utf-8"))
    nodes = [
        n for n in manifest["nodes"].values() if n["resource_type"] == "model" and n["fqn"][1] == "marts"
    ]
    assert [n["name"] for n in nodes] == ["fct_signups_by_channel"]
    [mart] = nodes
    assert mart["description"].strip()
    assert list(mart["columns"]) == [name for name, _ in CONTRACT_COLUMNS]
    for column in mart["columns"].values():
        assert column["description"].strip(), column["name"]
    docs = {d["name"]: d["block_contents"].strip() for d in manifest["docs"].values()}
    columns = mart["columns"]
    assert docs["customer"] in mart["description"]
    assert docs["acquisition_channel"] in columns["channel"]["description"]
    assert docs["channel"] in columns["channel"]["description"]
    assert docs["signup"] in columns["signups"]["description"]
    assert docs["ad_spend"] in columns["ad_spend"]["description"]


def test_mart_reads_no_staging_model(fixture_build: Path) -> None:
    manifest = json.loads((fixture_build / "target" / "manifest.json").read_text(encoding="utf-8"))
    parents = manifest["parent_map"]["model.retail_analytics.fct_signups_by_channel"]
    assert sorted(parents) == [
        "model.retail_analytics.dim_customers",
        "model.retail_analytics.int_channel_spend_daily",
        "seed.retail_analytics.channels",
    ]


def test_mart_tests_exist(fixture_build: Path) -> None:
    manifest = json.loads((fixture_build / "target" / "manifest.json").read_text(encoding="utf-8"))
    tests = {n["name"] for n in manifest["nodes"].values() if n["resource_type"] == "test"}
    for name in (
        "unique_combination_fct_signups_by_channel_channel__quarter",
        "not_null_fct_signups_by_channel_channel",
        "not_null_fct_signups_by_channel_quarter",
        "not_null_fct_signups_by_channel_signups",
        "not_null_fct_signups_by_channel_ad_spend",
        "relationships_fct_signups_by_channel_channel__channel__ref_channels_",
        "accepted_values_fct_signups_by_channel_is_simulated__False__True",
        "assert_signups_non_negative",
        "assert_signup_shares_sum_to_one",
        "assert_signups_prior_null_only_first_quarter",
        "assert_signups_grid_complete",
        "assert_signups_mart_totals_match",
    ):
        assert name in tests, name


def append_row(path: Path, line: str) -> None:
    path.write_text(path.read_text(encoding="utf-8") + line + "\n", encoding="utf-8")


# Broken variants: (fixture, row to append, dbt tests expected to fail).
BROKEN = {
    "unknown channel": (
        "dim_customers",
        "17,2024-05-01,online,TikTok",
        {
            "relationships_fct_signups_by_channel_channel__channel__ref_channels_",
            "assert_signups_grid_complete",
        },
    ),
    "duplicate spend key": (
        "int_channel_spend_daily",
        "Paid Social,2024-01-15,10.00",
        {"unique_combination_int_channel_spend_daily_channel__spend_date"},
    ),
}


@pytest.mark.parametrize("case", BROKEN, ids=list(BROKEN))
def test_broken_fixture_fails_its_test(case: str, tmp_path: Path) -> None:
    table, line, expected = BROKEN[case]
    intermediate = tmp_path / "intermediate"
    shutil.copytree(FIXTURES, intermediate)
    append_row(intermediate / f"{table}.csv", line)

    result = mart_build(intermediate, tmp_path)
    assert not result.success
    assert failed(result) >= expected, failed(result)


def test_spend_after_the_last_signup_extends_the_grid(tmp_path: Path) -> None:
    """Spend in a quarter with no sign-ups, after the last sign-up quarter, adds that quarter to the grid
    for every channel, and no spend is dropped."""
    intermediate = tmp_path / "intermediate"
    shutil.copytree(FIXTURES, intermediate)
    append_row(intermediate / "int_channel_spend_daily.csv", "Paid Search,2025-01-05,25.00")

    result = mart_build(intermediate, tmp_path)
    assert result.success, failed(result)
    assert rows(
        tmp_path,
        f"select count(*), sum(signups), sum(ad_spend) filter (where channel = 'Paid Search') "
        f"from {MART} where quarter = '2025-01-01'",
    ) == [(7, 0, Decimal("25.00"))]
    assert rows(tmp_path, f"select sum(ad_spend) from {MART}") == rows(
        tmp_path, "select sum(ad_spend) from intermediate.int_channel_spend_daily"
    )


# Singular tests run on a deliberately broken copy of the built mart: (update, dbt test expected to fail).
BROKEN_MART = {
    "negative sign-ups": (
        "update {mart} set signups = -1 where channel = 'Email' and quarter = '2024-01-01'",
        "assert_signups_non_negative",
    ),
    "shares do not sum to 1": (
        "update {mart} set share_of_signups = 0.9 where channel = 'Email' and quarter = '2024-01-01'",
        "assert_signup_shares_sum_to_one",
    ),
    "prior null after the first quarter": (
        "update {mart} set signups_prior_quarter = null where channel = 'Email' and quarter = '2024-04-01'",
        "assert_signups_prior_null_only_first_quarter",
    ),
    "gap in the grid": (
        "delete from {mart} where quarter = '2024-07-01'",
        "assert_signups_grid_complete",
    ),
    "sign-ups or spend lost": (
        "update {mart} set signups = signups + 1, ad_spend = ad_spend + 1 "
        "where channel = 'Email' and quarter = '2024-01-01'",
        "assert_signups_mart_totals_match",
    ),
    "not simulated": (
        "update {mart} set is_simulated = false where channel = 'Email'",
        "accepted_values_fct_signups_by_channel_is_simulated__False__True",
    ),
}


@pytest.mark.parametrize("case", BROKEN_MART, ids=list(BROKEN_MART))
def test_broken_mart_fails_its_test(case: str, tmp_path: Path) -> None:
    sql, expected = BROKEN_MART[case]
    result = mart_build(FIXTURES, tmp_path)
    assert result.success, failed(result)
    with duckdb.connect(str(tmp_path / "warehouse.duckdb")) as con:
        con.execute(sql.format(mart=MART))
    result = dbt_build(RAW_FIXTURES, tmp_path, select=("fct_signups_by_channel",), command="test")
    assert not result.success
    assert expected in failed(result), failed(result)


def test_seed_42_end_to_end(tmp_path: Path) -> None:
    """Generated sources through the mart: every dbt test passes, 7 channels x 8 quarters (2024Q1 to
    2025Q4), sign-ups sum to the customer count, spend sums to the staging spend; prints the latest
    quarter's sign-ups and cost per signup by channel (`pytest -s`)."""
    raw = tmp_path / "raw"
    generate(raw, 42)
    result = dbt_build(raw, tmp_path)
    assert result.success, failed(result)
    assert rows(tmp_path, f"select count(*), min(quarter), max(quarter) from {MART}") == [
        (56, date(2024, 1, 1), date(2025, 10, 1))
    ]
    assert rows(tmp_path, f"select sum(signups) from {MART}") == rows(
        tmp_path, "select count(*) from intermediate.dim_customers"
    )
    assert rows(tmp_path, f"select sum(ad_spend) from {MART}") == rows(
        tmp_path, "select sum(spend) from staging.stg_ad_spend"
    )
    latest = rows(
        tmp_path,
        f"select channel, signups, cost_per_signup from {MART} "
        f"where quarter = (select max(quarter) from {MART}) order by signups desc, channel",
    )
    print("\nLatest quarter (simulated): channel, sign-ups, cost per signup")
    for channel, signups, cost in latest:
        print(f"  {channel}: {signups}, {cost}")
    assert len(latest) == 7
    assert all(signups > 0 for _, signups, _ in latest)
