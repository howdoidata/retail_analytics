"""Checks for the C-9 customer cohorts mart (`fct_customer_cohorts`): built on hand-made fixtures shaped like
`dim_customers` and `int_customer_visits` (`tests/fixtures/intermediate/cohorts/`), each case of the story's
I/O matrix gives the expected rows, the horizon variable changes rows and never columns, broken fixtures and
broken copies of the mart fail their dbt test, the columns are the contract's in order, every column is
described, and on seed 42 every dbt test passes with 7 channels x every cohort quarter's offsets up to the
horizon or the data end."""

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

FIXTURES = INTERMEDIATE_FIXTURES / "cohorts"
MODEL = "fct_customer_cohorts"
MART = f"main.{MODEL}"
NODE = f"model.retail_analytics.{MODEL}"
CONTRACT_COLUMNS = [
    ("channel", "VARCHAR"),
    ("cohort_quarter", "DATE"),
    ("quarters_since_signup", "INTEGER"),
    ("cohort_size", "INTEGER"),
    ("active_customers", "INTEGER"),
    ("active_rate", "DECIMAL(18,6)"),
    ("visits", "INTEGER"),
    ("visits_per_active_customer", "DECIMAL(18,4)"),
    ("revenue", "DECIMAL(18,2)"),
    ("average_order", "DECIMAL(18,2)"),
    ("is_simulated", "BOOLEAN"),
]
Q1, Q2, Q3, Q4 = date(2024, 1, 1), date(2024, 4, 1), date(2024, 7, 1), date(2024, 10, 1)
CHANNELS = 7
# Fixture data ends in 2024 Q4, so with the default horizon (7) the Q1-Q4 cohorts have 4, 3, 2, 1 offsets.
DEFAULT_ROWS = CHANNELS * (4 + 3 + 2 + 1)


@pytest.fixture(scope="module")
def fixture_build(tmp_path_factory: pytest.TempPathFactory) -> Path:
    work = tmp_path_factory.mktemp("cohorts_fixtures")
    result = mart_build(FIXTURES, work, MODEL)
    assert result.success, failed(result)
    return work


def d(value: str | None) -> Decimal | None:
    return None if value is None else Decimal(value)


def cohort(work: Path, channel: str, quarter: date) -> list[tuple]:
    """(offset, size, active, rate, visits, per active, revenue, average order) for one cohort, by offset."""
    return rows(
        work,
        f"select quarters_since_signup, cohort_size, active_customers, active_rate, visits, "
        f"visits_per_active_customer, revenue, average_order from {MART} "
        f"where channel = '{channel}' and cohort_quarter = '{quarter}' order by quarters_since_signup",
    )


def expect(*offsets: tuple) -> list[tuple]:
    return [(o, s, a, d(r), v, d(p), d(rev), d(avg)) for o, s, a, r, v, p, rev, avg in offsets]


def columns(work: Path) -> list[tuple]:
    return rows(
        work,
        "select column_name, data_type from information_schema.columns where table_schema = 'main' "
        f"and table_name = '{MODEL}' order by ordinal_position",
    )


PAID_SOCIAL_Q1 = expect(
    (0, 4, 3, "0.75", 5, "1.6667", "250.00", "50.00"),
    (1, 4, 1, "0.25", 1, "1", "30.00", "30.00"),
    (2, 4, 0, "0", 0, None, "0.00", None),
    (3, 4, 1, "0.25", 1, "1", "70.00", "70.00"),
)


def test_columns_follow_the_contract(fixture_build: Path) -> None:
    assert columns(fixture_build) == CONTRACT_COLUMNS


def test_grid_and_totals(fixture_build: Path) -> None:
    """7 channels x Q1-Q4 2024 cohorts, offsets up to the 2024 Q4 data end; every customer on an offset-0 row
    once, every visit and dollar once, and is_simulated always true."""
    assert rows(
        fixture_build,
        f"select count(*), count(distinct channel), min(cohort_quarter), max(cohort_quarter), "
        f"sum(cohort_size) filter (where quarters_since_signup = 0), sum(visits), sum(revenue), "
        f"bool_and(is_simulated) from {MART}",
    ) == [(DEFAULT_ROWS, CHANNELS, Q1, Q4, 7, 10, Decimal("395.50"), True)]


def test_normal_cohort_quarter_boundary_and_inactive_quarter(fixture_build: Path) -> None:
    """I/O matrix: 4 Paid Social 2024 Q1 sign-ups; 3 visit in Q1 (5 visits, $250; one of them 3 times, so
    active 3, not 5). The sign-up on 31 March visits on 1 April: offset 1. Nobody visits at offset 2: active
    and rate 0, no visits per active customer or average order, revenue 0.00. One visit at offset 3."""
    assert cohort(fixture_build, "Paid Social", Q1) == PAID_SOCIAL_Q1


def test_empty_cohort(fixture_build: Path) -> None:
    """Referral has no Q2 sign-ups: a row for each offset up to the data end, size 0, rate null."""
    assert cohort(fixture_build, "Referral", Q2) == expect(
        (0, 0, 0, None, 0, None, "0.00", None),
        (1, 0, 0, None, 0, None, "0.00", None),
        (2, 0, 0, None, 0, None, "0.00", None),
    )


def test_cohort_without_visits(fixture_build: Path) -> None:
    assert cohort(fixture_build, "Referral", Q1) == expect(
        *[(o, 1, 0, "0", 0, None, "0.00", None) for o in range(4)]
    )


def test_young_cohorts(fixture_build: Path) -> None:
    """Data ends in 2024 Q4: the Q1 cohort has offsets 0-3, Q3 0-1, Q4 only 0; no later rows."""
    offsets = rows(
        fixture_build,
        f"select cohort_quarter, max(quarters_since_signup), count(*) from {MART} group by cohort_quarter "
        f"order by cohort_quarter",
    )
    assert offsets == [(Q1, 3, 4 * CHANNELS), (Q2, 2, 3 * CHANNELS), (Q3, 1, 2 * CHANNELS), (Q4, 0, CHANNELS)]
    assert cohort(fixture_build, "Paid Search", Q3) == expect(
        (0, 1, 1, "1", 1, "1", "10.00", "10.00"),
        (1, 1, 1, "1", 1, "1", "15.50", "15.50"),
    )
    assert cohort(fixture_build, "Email", Q4) == expect((0, 1, 1, "1", 1, "1", "20.00", "20.00"))


def test_horizon_1_drops_later_visits_and_rows(tmp_path: Path) -> None:
    """`--vars '{cohort_horizon_quarters: 1}'`: the Paid Social Q1 visit at offset 3 is not counted and there
    is no row for offsets 2 or 3; every dbt test still passes (totals count visits within the horizon)."""
    result = mart_build(FIXTURES, tmp_path, MODEL, extra_vars={"cohort_horizon_quarters": 1})
    assert result.success, failed(result)
    assert cohort(tmp_path, "Paid Social", Q1) == PAID_SOCIAL_Q1[:2]
    assert rows(tmp_path, f"select count(*), sum(visits), sum(revenue) from {MART}") == [
        (CHANNELS * (2 + 2 + 2 + 1), 9, Decimal("325.50"))
    ]
    assert columns(tmp_path) == CONTRACT_COLUMNS


def test_horizon_change_changes_rows_not_columns(tmp_path: Path) -> None:
    """Horizon 7 -> 2: same columns, fewer rows, offsets 0-2 identical."""
    result = mart_build(FIXTURES, tmp_path, MODEL, extra_vars={"cohort_horizon_quarters": 2})
    assert result.success, failed(result)
    assert cohort(tmp_path, "Paid Social", Q1) == PAID_SOCIAL_Q1[:3]
    assert rows(tmp_path, f"select max(quarters_since_signup), count(*) from {MART}") == [
        (2, CHANNELS * (3 + 3 + 2 + 1))
    ]
    assert columns(tmp_path) == CONTRACT_COLUMNS


def test_data_end_follows_the_latest_visit(tmp_path: Path) -> None:
    """A visit on 2025-01-10, after the last signup quarter (2024 Q4), moves the data end to 2025 Q1: the
    2024 Q4 cohort gets offsets 0-1 and Paid Social 2024 Q1 an offset-4 row with that 1 visit."""
    intermediate = tmp_path / "intermediate"
    shutil.copytree(FIXTURES, intermediate)
    append_row(intermediate / "int_customer_visits.csv", "1,5,111,2025-01-10,25.00,371,56")
    result = mart_build(intermediate, tmp_path, MODEL)
    assert result.success, failed(result)
    assert rows(
        tmp_path,
        f"select distinct quarters_since_signup from {MART} where cohort_quarter = '{Q4}' order by 1",
    ) == [(0,), (1,)]
    assert cohort(tmp_path, "Paid Social", Q1) == [
        *PAID_SOCIAL_Q1,
        *expect((4, 4, 1, "0.25", 1, "1", "25.00", "25.00")),
    ]


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
    cols = mart["columns"]
    assert docs["customer"] in mart["description"]
    assert docs["cohort"] in mart["description"]
    assert docs["acquisition_channel"] in cols["channel"]["description"]
    assert docs["channel"] in cols["channel"]["description"]
    assert docs["cohort"] in cols["quarters_since_signup"]["description"]
    assert docs["signup"] in cols["cohort_size"]["description"]
    assert docs["active_customer"] in cols["active_customers"]["description"]
    assert docs["visit"] in cols["visits"]["description"]


def test_every_marts_model_and_column_is_described(fixture_build: Path) -> None:
    """Every model in `marts`, not only this one, has a description and a description on every column."""
    manifest = json.loads((fixture_build / "target" / "manifest.json").read_text(encoding="utf-8"))
    marts = [
        n for n in manifest["nodes"].values() if n["resource_type"] == "model" and n["fqn"][1] == "marts"
    ]
    assert {n["name"] for n in marts} >= {"fct_signups_by_channel", "fct_visit_funnel_by_channel", MODEL}
    for mart in marts:
        assert mart["description"].strip(), mart["name"]
        assert mart["columns"], mart["name"]
        for column in mart["columns"].values():
            assert column["description"].strip(), (mart["name"], column["name"])


def test_mart_reads_only_dim_visits_and_seed(fixture_build: Path) -> None:
    manifest = json.loads((fixture_build / "target" / "manifest.json").read_text(encoding="utf-8"))
    assert sorted(manifest["parent_map"][NODE]) == [
        "model.retail_analytics.dim_customers",
        "model.retail_analytics.int_customer_visits",
        "seed.retail_analytics.channels",
    ]


UNIQUE = "unique_combination_fct_customer_cohorts_channel__cohort_quarter__quarters_since_signup"
RELATIONSHIPS = "relationships_fct_customer_cohorts_channel__channel__ref_channels_"
SIMULATED = "accepted_values_fct_customer_cohorts_is_simulated__False__True"
TESTS = (
    UNIQUE,
    RELATIONSHIPS,
    SIMULATED,
    *(
        f"not_null_fct_customer_cohorts_{column}"
        for column in (
            "channel",
            "cohort_quarter",
            "quarters_since_signup",
            "cohort_size",
            "active_customers",
            "visits",
            "revenue",
            "is_simulated",
        )
    ),
    "assert_cohorts_active_within_size",
    "assert_cohorts_active_rate_in_range",
    "assert_cohorts_no_rows_after_data_end",
    "assert_cohorts_grid_complete",
    "assert_cohorts_mart_totals_match",
)


def test_mart_tests_exist(fixture_build: Path) -> None:
    manifest = json.loads((fixture_build / "target" / "manifest.json").read_text(encoding="utf-8"))
    tests = {n["name"] for n in manifest["nodes"].values() if n["resource_type"] == "test"}
    for name in TESTS:
        assert name in tests, name


def append_row(path: Path, line: str) -> None:
    path.write_text(path.read_text(encoding="utf-8") + line + "\n", encoding="utf-8")


# Broken fixtures: (file, row to append, dbt tests expected to fail).
BROKEN = {
    "unknown channel": (
        "dim_customers.csv",
        "10,2024-02-01,online,TikTok",
        {RELATIONSHIPS, "assert_cohorts_grid_complete"},
    ),
    "visit before signup": (
        "int_customer_visits.csv",
        "7,2,111,2024-09-30,5.00,-62,-66",
        {"assert_cohorts_mart_totals_match"},
    ),
}


@pytest.mark.parametrize("case", BROKEN, ids=list(BROKEN))
def test_broken_fixture_fails_its_test(case: str, tmp_path: Path) -> None:
    file, line, expected = BROKEN[case]
    intermediate = tmp_path / "intermediate"
    shutil.copytree(FIXTURES, intermediate)
    append_row(intermediate / file, line)

    result = mart_build(intermediate, tmp_path, MODEL)
    assert not result.success
    assert failed(result) >= expected, failed(result)


PS_Q1 = "channel = 'Paid Social' and cohort_quarter = '2024-01-01'"
# Tests run on a deliberately broken copy of the built mart: (SQL, test expected to fail).
BROKEN_MART = {
    "more active than the cohort": (
        f"update {{mart}} set active_customers = 5 where {PS_Q1} and quarters_since_signup = 0",
        "assert_cohorts_active_within_size",
    ),
    "cohort size differs across offsets": (
        f"update {{mart}} set cohort_size = 9 where {PS_Q1} and quarters_since_signup = 2",
        "assert_cohorts_active_within_size",
    ),
    "active rate above 1": (
        f"update {{mart}} set active_rate = 1.5 where {PS_Q1} and quarters_since_signup = 0",
        "assert_cohorts_active_rate_in_range",
    ),
    "negative active rate": (
        f"update {{mart}} set active_rate = -0.1 where {PS_Q1} and quarters_since_signup = 0",
        "assert_cohorts_active_rate_in_range",
    ),
    "rate on an empty cohort": (
        "update {mart} set active_rate = 0 where channel = 'Referral' and cohort_quarter = '2024-04-01'",
        "assert_cohorts_active_rate_in_range",
    ),
    "rate missing on a non-empty cohort": (
        f"update {{mart}} set active_rate = null where {PS_Q1} and quarters_since_signup = 2",
        "assert_cohorts_active_rate_in_range",
    ),
    "visits per active customer with nobody active": (
        f"update {{mart}} set visits_per_active_customer = 0 where {PS_Q1} and quarters_since_signup = 2",
        "assert_cohorts_active_rate_in_range",
    ),
    "visits per active customer missing": (
        f"update {{mart}} set visits_per_active_customer = null where {PS_Q1} and quarters_since_signup = 0",
        "assert_cohorts_active_rate_in_range",
    ),
    "average order with no visits": (
        f"update {{mart}} set average_order = 0 where {PS_Q1} and quarters_since_signup = 2",
        "assert_cohorts_active_rate_in_range",
    ),
    "average order missing": (
        f"update {{mart}} set average_order = null where {PS_Q1} and quarters_since_signup = 0",
        "assert_cohorts_active_rate_in_range",
    ),
    "row after the data ends": (
        f"insert into {{mart}} select * replace (4 as quarters_since_signup) from {{mart}} "
        f"where {PS_Q1} and quarters_since_signup = 3",
        "assert_cohorts_no_rows_after_data_end",
    ),
    "grid row missing": (
        f"delete from {{mart}} where {PS_Q1} and quarters_since_signup = 2",
        "assert_cohorts_grid_complete",
    ),
    "extra grid row": (
        "insert into {mart} select * replace ('TikTok' as channel) from {mart} "
        f"where {PS_Q1} and quarters_since_signup = 0",
        "assert_cohorts_grid_complete",
    ),
    "customers counted twice": (
        f"update {{mart}} set cohort_size = cohort_size + 1 where {PS_Q1}",
        "assert_cohorts_mart_totals_match",
    ),
    "visits lost": (
        f"update {{mart}} set visits = visits - 1 where {PS_Q1} and quarters_since_signup = 0",
        "assert_cohorts_mart_totals_match",
    ),
    "revenue lost": (
        f"update {{mart}} set revenue = revenue - 1 where {PS_Q1} and quarters_since_signup = 0",
        "assert_cohorts_mart_totals_match",
    ),
    "duplicate key": (
        f"insert into {{mart}} select * from {{mart}} where {PS_Q1} and quarters_since_signup = 1",
        UNIQUE,
    ),
    "null visits": (
        f"update {{mart}} set visits = null where {PS_Q1} and quarters_since_signup = 2",
        "not_null_fct_customer_cohorts_visits",
    ),
    "not simulated": (
        "update {mart} set is_simulated = false where channel = 'Email'",
        SIMULATED,
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


def test_seed_42_end_to_end(tmp_path: Path) -> None:
    """Generated sources through the mart: every dbt test passes, rows = 7 x the sum over cohort quarters of
    min(horizon + 1, quarters until the data end + 1), offset-0 rows sum to the customer count; prints the
    Paid Social 2024 Q1 cohort (`pytest -s`)."""
    raw = tmp_path / "raw"
    generate(raw, 42)
    result = dbt_build(raw, tmp_path)
    assert result.success, failed(result)
    [(expected_rows,)] = rows(
        tmp_path,
        """
        with data_end as (
            select date_trunc('quarter', max(data_date)) as data_end_quarter
            from (
                select signup_date as data_date from intermediate.dim_customers
                union all
                select visit_date from intermediate.int_customer_visits
            )
        ),
        quarters as (
            select unnest(generate_series(
                min(date_trunc('quarter', signup_date))::timestamp,
                max(date_trunc('quarter', signup_date))::timestamp,
                interval 3 month
            )) as cohort_quarter
            from intermediate.dim_customers
        )
        select 7 * sum(least(8, date_diff('quarter', cohort_quarter, data_end_quarter) + 1))
        from quarters cross join data_end
        """,
    )
    assert rows(tmp_path, f"select count(*) from {MART}") == [(expected_rows,)]
    assert rows(tmp_path, f"select sum(cohort_size) from {MART} where quarters_since_signup = 0") == rows(
        tmp_path, "select count(*) from intermediate.dim_customers"
    )
    paid_social = rows(
        tmp_path,
        f"select quarters_since_signup, cohort_size, active_rate, visits_per_active_customer, average_order "
        f"from {MART} where channel = 'Paid Social' and cohort_quarter = '2024-01-01' "
        f"order by quarters_since_signup",
    )
    print(
        f"\nRows: {expected_rows}. Paid Social 2024 Q1 cohort (simulated): offset, size, active rate, "
        "visits per active customer, average order"
    )
    for offset, size, rate, per_active, average in paid_social:
        print(f"  {offset}: {size}, {rate}, {per_active}, {average}")
    assert [o for o, *_ in paid_social] == list(range(8))
    assert len({size for _, size, *_ in paid_social}) == 1
