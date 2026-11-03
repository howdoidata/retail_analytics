"""Checks for the C-8 visit funnel mart (`fct_visit_funnel_by_channel`): built on hand-made fixtures shaped
like `dim_customers` (with milestone dates) and `int_channel_spend_daily`
(`tests/fixtures/intermediate/funnel/`), each case of the story's I/O matrix gives the expected rows, the
milestone variable changes rows and never columns, broken fixtures and broken copies of the mart fail their
dbt test, the columns are the contract's in order, every column is described, and on seed 42 every dbt test
passes with 7 channels x 24 months x 6 milestones."""

from __future__ import annotations

import json
import shutil
from datetime import date
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest
from mart_fixtures import INTERMEDIATE_FIXTURES, mart_build
from test_staging import FIXTURES as RAW_FIXTURES
from test_staging import dbt_build, failed, rows

from retail_analytics.generator import generate

FIXTURES = INTERMEDIATE_FIXTURES / "funnel"
MODEL = "fct_visit_funnel_by_channel"
MART = f"main.{MODEL}"
NODE = f"model.retail_analytics.{MODEL}"
CONTRACT_COLUMNS = [
    ("channel", "VARCHAR"),
    ("cohort_month", "DATE"),
    ("milestone", "INTEGER"),
    ("previous_milestone", "INTEGER"),
    ("customers_reached", "INTEGER"),
    ("step_rate", "DECIMAL(18,6)"),
    ("avg_days_from_previous", "DECIMAL(18,2)"),
    ("ad_spend", "DECIMAL(18,2)"),
    ("is_simulated", "BOOLEAN"),
]
JAN, FEB, MAR = date(2024, 1, 1), date(2024, 2, 1), date(2024, 3, 1)
CHANNELS = 7


@pytest.fixture(scope="module")
def fixture_build(tmp_path_factory: pytest.TempPathFactory) -> Path:
    work = tmp_path_factory.mktemp("funnel_fixtures")
    result = mart_build(FIXTURES, work, MODEL)
    assert result.success, failed(result)
    return work


def d(value: str | None) -> Decimal | None:
    return None if value is None else Decimal(value)


def cohort(work: Path, channel: str, month: date) -> list[tuple]:
    """(milestone, previous, reached, step_rate, avg_days, ad_spend) for one cohort, by milestone."""
    return rows(
        work,
        f"select milestone, previous_milestone, customers_reached, step_rate, avg_days_from_previous, "
        f"ad_spend from {MART} where channel = '{channel}' and cohort_month = '{month}' order by milestone",
    )


def expect(*steps: tuple) -> list[tuple]:
    return [(m, p, r, d(s), d(a), d(sp)) for m, p, r, s, a, sp in steps]


def test_columns_follow_the_contract(fixture_build: Path) -> None:
    assert (
        rows(
            fixture_build,
            "select column_name, data_type from information_schema.columns where table_schema = 'main' "
            "and table_name = 'fct_visit_funnel_by_channel' order by ordinal_position",
        )
        == CONTRACT_COLUMNS
    )


def test_grid_and_totals(fixture_build: Path) -> None:
    """7 channels x Jan-Mar (March only has spend) x 6 milestones; every customer on a signup row once,
    every dollar once, and is_simulated always true."""
    assert rows(
        fixture_build,
        f"select count(*), count(distinct channel), min(cohort_month), max(cohort_month), "
        f"sum(customers_reached) filter (where milestone = 0), sum(ad_spend), bool_and(is_simulated) "
        f"from {MART}",
    ) == [(CHANNELS * 3 * 6, CHANNELS, JAN, MAR, 9, Decimal("405.00"), True)]


def test_normal_cohort_days_and_spend(fixture_build: Path) -> None:
    """I/O matrix: 4 Paid Social Jan customers (the one on 31 Jan included), 3 reach visit 1 on days 0, 2,
    4 after signup (2.00), 2 reach visit 2 10 and 20 days after visit 1 (15.00); nobody reaches visit 3
    (step 0, previous 2 > 0) or 5 (step null, previous 0); $300 spend on the signup row only."""
    assert cohort(fixture_build, "Paid Social", JAN) == expect(
        (0, None, 4, None, None, "300.00"),
        (1, 0, 3, "0.75", "2.00", None),
        (2, 1, 2, "0.666667", "15.00", None),
        (3, 2, 0, "0", None, None),
        (5, 3, 0, None, None, None),
        (10, 5, 0, None, None, None),
    )


def test_month_boundary(fixture_build: Path) -> None:
    """The sign-up on 1 Feb is the February cohort, not January's; Paid Social has no February spend."""
    assert cohort(fixture_build, "Paid Social", FEB) == expect(
        (0, None, 1, None, None, "0.00"),
        (1, 0, 1, "1", "4.00", None),
        (2, 1, 0, "0", None, None),
        (3, 2, 0, None, None, None),
        (5, 3, 0, None, None, None),
        (10, 5, 0, None, None, None),
    )


def test_no_spend(fixture_build: Path) -> None:
    assert cohort(fixture_build, "Email", JAN)[:3] == expect(
        (0, None, 1, None, None, "0.00"),
        (1, 0, 1, "1", "1.00", None),
        (2, 1, 0, "0", None, None),
    )


def test_nobody_reaches_visit_1(fixture_build: Path) -> None:
    assert cohort(fixture_build, "Referral", JAN)[:3] == expect(
        (0, None, 1, None, None, "0.00"),
        (1, 0, 0, "0", None, None),
        (2, 1, 0, None, None, None),
    )


def test_empty_cohort(fixture_build: Path) -> None:
    """Referral has no February customers: every milestone row is there with 0 and no rate or days."""
    assert cohort(fixture_build, "Referral", FEB) == expect(
        (0, None, 0, None, None, "0.00"),
        (1, 0, 0, None, None, None),
        (2, 1, 0, None, None, None),
        (3, 2, 0, None, None, None),
        (5, 3, 0, None, None, None),
        (10, 5, 0, None, None, None),
    )


def test_later_steps(fixture_build: Path) -> None:
    """Paid Search Feb: days from the previous milestone's date at every step (visit 3 to visit 5 is 13 Feb
    to 1 Mar 2024, 17 days); a later step reached by nobody after one reached by some has step 0."""
    assert cohort(fixture_build, "Paid Search", FEB) == expect(
        (0, None, 2, None, None, "80.00"),
        (1, 0, 2, "1", "1.50", None),
        (2, 1, 2, "1", "3.00", None),
        (3, 2, 2, "1", "3.50", None),
        (5, 3, 1, "0.5", "17.00", None),
        (10, 5, 0, "0", None, None),
    )


def test_spend_only_month(fixture_build: Path) -> None:
    """March has only Paid Search spend: it is in the grid for every channel, with the spend on Paid
    Search's signup row."""
    assert cohort(fixture_build, "Paid Search", MAR)[:2] == expect(
        (0, None, 0, None, None, "25.00"),
        (1, 0, 0, None, None, None),
    )
    march = rows(fixture_build, f"select count(*) from {MART} where cohort_month = '{MAR}'")
    assert march == [(CHANNELS * 6,)]


def test_milestone_var_override_changes_rows_not_columns(tmp_path: Path) -> None:
    """`--vars '{milestones: [4, 1, 4]}'`: milestones 0, 1, 4 (deduplicated, sorted), previous of 4 is 1,
    with no code or YAML edit; the columns are unchanged."""
    result = mart_build(FIXTURES, tmp_path, MODEL, extra_vars={"milestones": [4, 1, 4]})
    assert result.success, failed(result)
    assert cohort(tmp_path, "Paid Search", FEB) == expect(
        (0, None, 2, None, None, "80.00"),
        (1, 0, 2, "1", "1.50", None),
        (4, 1, 1, "0.5", "10.00", None),
    )
    assert cohort(tmp_path, "Paid Social", JAN) == expect(
        (0, None, 4, None, None, "300.00"),
        (1, 0, 3, "0.75", "2.00", None),
        (4, 1, 0, "0", None, None),
    )
    assert rows(tmp_path, f"select count(*) from {MART}") == [(CHANNELS * 3 * 3,)]
    assert (
        rows(
            tmp_path,
            "select column_name, data_type from information_schema.columns where table_schema = 'main' "
            "and table_name = 'fct_visit_funnel_by_channel' order by ordinal_position",
        )
        == CONTRACT_COLUMNS
    )


def test_every_mart_node_is_described(fixture_build: Path) -> None:
    """The mart and every column have a description, the documented columns are the contract's in order,
    and the shared terms come from doc blocks."""
    manifest = json.loads((fixture_build / "target" / "manifest.json").read_text(encoding="utf-8"))
    mart = manifest["nodes"][NODE]
    assert mart["description"].strip()
    assert list(mart["columns"]) == [name for name, _ in CONTRACT_COLUMNS]
    for column in mart["columns"].values():
        assert column["description"].strip(), column["name"]
    docs = {d["name"]: d["block_contents"].strip() for d in manifest["docs"].values()}
    columns = mart["columns"]
    assert docs["customer"] in mart["description"]
    assert docs["milestone"] in mart["description"]
    assert docs["acquisition_channel"] in columns["channel"]["description"]
    assert docs["channel"] in columns["channel"]["description"]
    assert docs["milestone"] in columns["milestone"]["description"]
    assert docs["signup"] in columns["customers_reached"]["description"]
    assert docs["step_rate"] in columns["step_rate"]["description"]
    assert docs["ad_spend"] in columns["ad_spend"]["description"]


def test_every_marts_model_and_column_is_described(fixture_build: Path) -> None:
    """Every model in `marts`, not only this one, has a description and a description on every column."""
    manifest = json.loads((fixture_build / "target" / "manifest.json").read_text(encoding="utf-8"))
    marts = [
        n for n in manifest["nodes"].values() if n["resource_type"] == "model" and n["fqn"][1] == "marts"
    ]
    assert {n["name"] for n in marts} >= {"fct_signups_by_channel", MODEL}
    for mart in marts:
        assert mart["description"].strip(), mart["name"]
        assert mart["columns"], mart["name"]
        for column in mart["columns"].values():
            assert column["description"].strip(), (mart["name"], column["name"])


def test_mart_reads_only_dim_spend_and_seed(fixture_build: Path) -> None:
    manifest = json.loads((fixture_build / "target" / "manifest.json").read_text(encoding="utf-8"))
    assert sorted(manifest["parent_map"][NODE]) == [
        "model.retail_analytics.dim_customers",
        "model.retail_analytics.int_channel_spend_daily",
        "seed.retail_analytics.channels",
    ]


TESTS = (
    "unique_combination_fct_visit_funnel_by_channel_channel__cohort_month__milestone",
    "not_null_fct_visit_funnel_by_channel_channel",
    "not_null_fct_visit_funnel_by_channel_cohort_month",
    "not_null_fct_visit_funnel_by_channel_milestone",
    "not_null_fct_visit_funnel_by_channel_customers_reached",
    "not_null_fct_visit_funnel_by_channel_is_simulated",
    "relationships_fct_visit_funnel_by_channel_channel__channel__ref_channels_",
    "accepted_values_fct_visit_funnel_by_channel_is_simulated__False__True",
    "assert_funnel_reached_non_increasing",
    "assert_funnel_step_rate_in_range",
    "assert_funnel_signup_row_nulls",
    "assert_funnel_avg_days_non_negative",
    "assert_funnel_grid_complete",
    "assert_funnel_mart_totals_match",
)


def test_mart_tests_exist(fixture_build: Path) -> None:
    manifest = json.loads((fixture_build / "target" / "manifest.json").read_text(encoding="utf-8"))
    tests = {n["name"] for n in manifest["nodes"].values() if n["resource_type"] == "test"}
    for name in TESTS:
        assert name in tests, name


def append_row(path: Path, line: str) -> None:
    path.write_text(path.read_text(encoding="utf-8") + line + "\n", encoding="utf-8")


EMPTY_MAP = '"{1=NULL, 2=NULL, 3=NULL, 4=NULL, 5=NULL, 10=NULL}"'
# Broken fixtures: (row to append to dim_customers, dbt tests expected to fail).
BROKEN = {
    "unknown channel": (
        f"10,2024-02-01,online,TikTok,{EMPTY_MAP}",
        {
            "relationships_fct_visit_funnel_by_channel_channel__channel__ref_channels_",
            "assert_funnel_grid_complete",
        },
    ),
    "visit before signup": (
        '10,2024-02-20,online,Email,"{1=2024-02-01, 2=NULL, 3=NULL, 4=NULL, 5=NULL, 10=NULL}"',
        {"assert_funnel_avg_days_non_negative"},
    ),
    "later visit reached without the earlier one": (
        '10,2024-02-20,online,Email,"{1=NULL, 2=2024-02-21, 3=NULL, 4=NULL, 5=NULL, 10=NULL}"',
        {"assert_funnel_reached_non_increasing"},
    ),
}


@pytest.mark.parametrize("case", BROKEN, ids=list(BROKEN))
def test_broken_fixture_fails_its_test(case: str, tmp_path: Path) -> None:
    line, expected = BROKEN[case]
    intermediate = tmp_path / "intermediate"
    shutil.copytree(FIXTURES, intermediate)
    append_row(intermediate / "dim_customers.csv", line)

    result = mart_build(intermediate, tmp_path, MODEL)
    assert not result.success
    assert failed(result) >= expected, failed(result)


PS_JAN = "channel = 'Paid Social' and cohort_month = '2024-01-01'"
# Tests run on a deliberately broken copy of the built mart: (SQL, test expected to fail).
BROKEN_MART = {
    "reached rises": (
        f"update {{mart}} set customers_reached = 9 where {PS_JAN} and milestone = 2",
        "assert_funnel_reached_non_increasing",
    ),
    "step rate above 1": (
        f"update {{mart}} set step_rate = 1.5 where {PS_JAN} and milestone = 1",
        "assert_funnel_step_rate_in_range",
    ),
    "signup row has a previous milestone": (
        f"update {{mart}} set previous_milestone = 0 where {PS_JAN} and milestone = 0",
        "assert_funnel_signup_row_nulls",
    ),
    "step rate missing after a reached step": (
        f"update {{mart}} set step_rate = null where {PS_JAN} and milestone = 1",
        "assert_funnel_signup_row_nulls",
    ),
    "spend off the signup row": (
        f"update {{mart}} set ad_spend = 0 where {PS_JAN} and milestone = 1",
        "assert_funnel_signup_row_nulls",
    ),
    "wrong previous milestone": (
        f"update {{mart}} set previous_milestone = 2 where {PS_JAN} and milestone = 5",
        "assert_funnel_grid_complete",
    ),
    "step rate on the signup row": (
        f"update {{mart}} set step_rate = 0.5 where {PS_JAN} and milestone = 0",
        "assert_funnel_signup_row_nulls",
    ),
    "days on the signup row": (
        f"update {{mart}} set avg_days_from_previous = 1 where {PS_JAN} and milestone = 0",
        "assert_funnel_signup_row_nulls",
    ),
    "days missing where customers reached": (
        f"update {{mart}} set avg_days_from_previous = null where {PS_JAN} and milestone = 1",
        "assert_funnel_signup_row_nulls",
    ),
    "step rate after a step nobody reached": (
        f"update {{mart}} set step_rate = 0 where {PS_JAN} and milestone = 5",
        "assert_funnel_signup_row_nulls",
    ),
    "negative days": (
        f"update {{mart}} set avg_days_from_previous = -1 where {PS_JAN} and milestone = 1",
        "assert_funnel_avg_days_non_negative",
    ),
    "gap in the grid": (
        "delete from {mart} where cohort_month = '2024-02-01'",
        "assert_funnel_grid_complete",
    ),
    "milestone missing": (
        "delete from {mart} where milestone = 10",
        "assert_funnel_grid_complete",
    ),
    "customers or spend lost": (
        f"update {{mart}} set customers_reached = customers_reached + 1, ad_spend = ad_spend + 1 "
        f"where {PS_JAN} and milestone = 0",
        "assert_funnel_mart_totals_match",
    ),
    "duplicate key": (
        f"insert into {{mart}} select * from {{mart}} where {PS_JAN} and milestone = 10",
        "unique_combination_fct_visit_funnel_by_channel_channel__cohort_month__milestone",
    ),
    "null customers_reached": (
        f"update {{mart}} set customers_reached = null where {PS_JAN} and milestone = 10",
        "not_null_fct_visit_funnel_by_channel_customers_reached",
    ),
    "not simulated": (
        "update {mart} set is_simulated = false where channel = 'Email'",
        "accepted_values_fct_visit_funnel_by_channel_is_simulated__False__True",
    ),
}


@pytest.mark.parametrize("case", BROKEN_MART, ids=list(BROKEN_MART))
def test_broken_mart_fails_its_test(case: str, tmp_path: Path) -> None:
    sql, expected = BROKEN_MART[case]
    result = mart_build(FIXTURES, tmp_path, MODEL)
    assert result.success, failed(result)
    with duckdb.connect(str(tmp_path / "warehouse.duckdb")) as con:
        con.execute(sql.format(mart=MART))
    result = dbt_build(RAW_FIXTURES, tmp_path, select=(MODEL,), command="test")
    assert not result.success
    assert expected in failed(result), failed(result)


def pooled(work: Path, channel: str) -> list[tuple]:
    """The contract's roll-up rule over every cohort: sum customers_reached, recompute step_rate from the
    sums, weight avg_days_from_previous by customers_reached."""
    return rows(
        work,
        f"""
        with summed as (
            select
                milestone,
                sum(customers_reached) as reached,
                sum(avg_days_from_previous * customers_reached) / nullif(
                    sum(customers_reached) filter (where avg_days_from_previous is not null), 0
                ) as avg_days,
            from {MART}
            where channel = '{channel}'
            group by milestone
        )
        select
            milestone,
            reached,
            round(reached / lag(reached) over (order by milestone), 6) as step_rate,
            round(avg_days, 2) as avg_days,
        from summed
        order by milestone
        """,
    )


def test_seed_42_end_to_end(tmp_path: Path) -> None:
    """Generated sources through the mart: every dbt test passes, 7 channels x 24 months (2024-01 to
    2025-12) x 6 milestones, signup rows sum to the customer count; prints the Paid Social funnel pooled
    over all cohorts (`pytest -s`)."""
    raw = tmp_path / "raw"
    generate(raw, 42)
    result = dbt_build(raw, tmp_path)
    assert result.success, failed(result)
    assert rows(tmp_path, f"select count(*), min(cohort_month), max(cohort_month) from {MART}") == [
        (CHANNELS * 24 * 6, date(2024, 1, 1), date(2025, 12, 1))
    ]
    assert rows(tmp_path, f"select sum(customers_reached) from {MART} where milestone = 0") == rows(
        tmp_path, "select count(*) from intermediate.dim_customers"
    )
    funnel = pooled(tmp_path, "Paid Social")
    print("\nPaid Social funnel, all cohorts pooled (simulated): milestone, reached, step rate, avg days")
    for milestone, reached, step_rate, avg_days in funnel:
        print(f"  {milestone}: {reached}, {step_rate}, {avg_days}")
    assert [m for m, *_ in funnel] == [0, 1, 2, 3, 5, 10]
    assert all(later <= earlier for (_, earlier, *_), (_, later, *_) in zip(funnel, funnel[1:], strict=False))
