"""Checks for the C-6 core customer layers (`int_customer_visits`, `dim_customers`): built on hand-made
staging-shaped fixtures (`tests/fixtures/staging/`) loaded into a `staging` schema, each case of the
story's I/O matrix gives the expected rows, a broken fixture fails its dbt test, the milestone variable
changes only the map keys, every column is described, and on seed 42 every dbt test passes."""

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

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "staging"
INTERMEDIATE_MODELS = ("int_customer_visits", "dim_customers")
# Column types of the staging models the intermediate layer reads, in model column order.
STAGING_TYPES = {
    "stg_customers": {
        "id": "bigint",
        "created_at": "timestamp",
        "email": "varchar",
        "first_name": "varchar",
        "last_name": "varchar",
        "state": "varchar",
        "signup_location": "varchar",
        "accepts_marketing": "boolean",
    },
    "stg_orders": {
        "id": "bigint",
        "customer_id": "bigint",
        "created_at": "timestamp",
        "sales_channel": "varchar",
        "status": "varchar",
        "subtotal": "decimal(12, 2)",
        "discount": "decimal(12, 2)",
        "total": "decimal(12, 2)",
        "currency": "varchar",
    },
    "stg_marketing_touches": {
        "id": "bigint",
        "customer_email": "varchar",
        "touched_at": "timestamp",
        "channel": "varchar",
        "campaign": "varchar",
        "utm_source": "varchar",
        "utm_source_channel": "varchar",
        "utm_medium": "varchar",
        "utm_campaign": "varchar",
    },
}


def core_build(staging_dir: Path, work: Path, extra_vars: dict | None = None) -> dbtRunnerResult:
    """Load the staging fixtures and the `channels` seed into the `staging` schema of
    `work/warehouse.duckdb`, then `dbt build --select intermediate` (models and their tests) on top."""
    with duckdb.connect(str(work / "warehouse.duckdb")) as con:
        con.execute("create schema staging")
        for table, types in STAGING_TYPES.items():
            columns = ", ".join(f"'{name}': '{kind}'" for name, kind in types.items())
            con.execute(
                f"create table staging.{table} as select * from read_csv("
                f"'{staging_dir / f'{table}.csv'}', header = true, columns = {{{columns}}})"
            )
        con.execute(
            f"create table staging.channels as select * from read_csv("
            f"'{DBT_DIR / 'seeds' / 'channels.csv'}', header = true, columns = {{'channel': 'varchar'}})"
        )
    return dbt_build(RAW_FIXTURES, work, select=("intermediate",), extra_vars=extra_vars)


@pytest.fixture(scope="module")
def fixture_build(tmp_path_factory: pytest.TempPathFactory) -> Path:
    work = tmp_path_factory.mktemp("core_fixtures")
    result = core_build(FIXTURES, work)
    assert result.success, failed(result)
    return work


def test_staging_fixtures_match_staging_columns() -> None:
    """The fixtures have exactly the columns of the staging models they stand in for."""
    staging_yml = (
        Path(__file__).resolve().parents[1] / "dbt" / "models" / "staging" / "_staging.yml"
    ).read_text(encoding="utf-8")
    for table, types in STAGING_TYPES.items():
        header = (FIXTURES / f"{table}.csv").read_text(encoding="utf-8").split("\n", 1)[0]
        assert header == ",".join(types), table
        block = staging_yml.split(f"- name: {table}\n", 1)[1].split("\n  - name: ", 1)[0]
        documented = [line.split("- name: ")[1] for line in block.splitlines() if "      - name: " in line]
        assert documented == list(types), table


def test_customer_visits(fixture_build: Path) -> None:
    """Visits numbered by time then order id (103 before 105 at the same minute), calendar days since
    signup (0 for a visit on the signup day) and since the previous visit (0 on the same day, null on
    visit 1); a customer with no orders has no rows."""
    assert rows(
        fixture_build, "select * from intermediate.int_customer_visits order by customer_id, visit_number"
    ) == [
        (1, 1, 101, date(2024, 1, 10), Decimal("100.00"), 5, None),
        (1, 2, 103, date(2024, 2, 11), Decimal("30.00"), 37, 32),
        (1, 3, 105, date(2024, 2, 11), Decimal("45.00"), 37, 0),
        (2, 1, 102, date(2024, 1, 6), Decimal("80.00"), 0, None),
        (4, 1, 201, date(2024, 2, 12), Decimal("60.00"), 2, None),
        (4, 2, 202, date(2024, 3, 1), Decimal("25.50"), 20, 18),
        (4, 3, 203, date(2024, 3, 1), Decimal("40.00"), 20, 0),
        (4, 4, 204, date(2024, 4, 15), Decimal("120.00"), 65, 45),
        (4, 5, 205, date(2024, 5, 1), Decimal("75.00"), 81, 16),
    ]


def test_dim_customers(fixture_build: Path) -> None:
    """First touch: customer 1, earliest of two pre-signup channels (Paid Social, though not the lowest id),
    a later Email touch ignored; customer 2, In-store touch at the signup time; customer 3, two touches at
    the same time, lowest id (Referral) wins; customer 4, earliest pre-signup touch (Email) over a later
    pre-signup Referral and a post-signup Paid Search. Every milestone is a key; null when not reached;
    customer 3 has no visits, so every date is null."""
    assert rows(fixture_build, "select * from intermediate.dim_customers order by customer_id") == [
        (1, date(2024, 1, 5), "online", "Paid Social",
         {1: date(2024, 1, 10), 2: date(2024, 2, 11), 3: date(2024, 2, 11), 5: None, 10: None}),
        (2, date(2024, 1, 6), "store", "In-store",
         {1: date(2024, 1, 6), 2: None, 3: None, 5: None, 10: None}),
        (3, date(2024, 2, 1), "online", "Referral", {1: None, 2: None, 3: None, 5: None, 10: None}),
        (4, date(2024, 2, 10), "online", "Email",
         {1: date(2024, 2, 12), 2: date(2024, 3, 1), 3: date(2024, 3, 1), 5: date(2024, 5, 1), 10: None}),
    ]  # fmt: skip


def test_milestone_dates_column_is_a_map(fixture_build: Path) -> None:
    [(kind,)] = rows(
        fixture_build,
        "select data_type from information_schema.columns "
        "where table_schema = 'intermediate' and table_name = 'dim_customers' "
        "and column_name = 'milestone_dates'",
    )
    assert kind == "MAP(INTEGER, DATE)"
    assert rows(
        fixture_build, "select milestone_dates[3] from intermediate.dim_customers where customer_id = 4"
    ) == [(date(2024, 3, 1),)]


def test_milestone_var_override_changes_only_map_keys(tmp_path: Path) -> None:
    """`--vars '{milestones: [4, 1]}'`: keys become 1, 4 (sorted) with no code or YAML edit; the schema is
    unchanged and every dbt test still passes."""
    result = core_build(FIXTURES, tmp_path, extra_vars={"milestones": [4, 1]})
    assert result.success, failed(result)
    assert rows(
        tmp_path, "select customer_id, milestone_dates from intermediate.dim_customers order by 1"
    ) == [
        (1, {1: date(2024, 1, 10), 4: None}),
        (2, {1: date(2024, 1, 6), 4: None}),
        (3, {1: None, 4: None}),
        (4, {1: date(2024, 2, 12), 4: date(2024, 4, 15)}),
    ]


def test_every_intermediate_node_is_described(fixture_build: Path) -> None:
    """Every intermediate model and column has a description, the documented columns are exactly the built
    columns, and the shared terms come from doc blocks."""
    manifest = json.loads((fixture_build / "target" / "manifest.json").read_text(encoding="utf-8"))
    nodes = [
        n
        for n in manifest["nodes"].values()
        if n["resource_type"] == "model" and n["fqn"][1] == "intermediate"
    ]
    assert sorted(n["name"] for n in nodes) == sorted(INTERMEDIATE_MODELS)
    for node in nodes:
        assert node["description"].strip(), node["unique_id"]
        for column in node["columns"].values():
            assert column["description"].strip(), f"{node['unique_id']}.{column['name']}"
        built = rows(
            fixture_build,
            f"select column_name from information_schema.columns "
            f"where table_schema = 'intermediate' and table_name = '{node['name']}' "
            "order by ordinal_position",
        )
        assert list(node["columns"]) == [c for (c,) in built], node["name"]
    docs = {d["name"]: d["block_contents"].strip() for d in manifest["docs"].values()}
    by_name = {n["name"]: n for n in nodes}
    dim = by_name["dim_customers"]
    assert docs["customer"] in dim["description"]
    assert docs["visit"] in by_name["int_customer_visits"]["description"]
    assert docs["acquisition_channel"] in dim["columns"]["acquisition_channel"]["description"]
    assert docs["channel"] in dim["columns"]["acquisition_channel"]["description"]
    assert docs["milestone"] in dim["columns"]["milestone_dates"]["description"]


def test_intermediate_tests_exist(fixture_build: Path) -> None:
    manifest = json.loads((fixture_build / "target" / "manifest.json").read_text(encoding="utf-8"))
    tests = {n["name"] for n in manifest["nodes"].values() if n["resource_type"] == "test"}
    for name in (
        "unique_combination_int_customer_visits_customer_id__visit_number",
        "not_null_int_customer_visits_customer_id",
        "not_null_int_customer_visits_visit_number",
        "unique_int_customer_visits_order_id",
        "relationships_int_customer_visits_customer_id__id__ref_stg_customers_",
        "unique_dim_customers_customer_id",
        "not_null_dim_customers_customer_id",
        "relationships_dim_customers_customer_id__id__ref_stg_customers_",
        "not_null_dim_customers_acquisition_channel",
        "relationships_dim_customers_acquisition_channel__channel__ref_channels_",
        "assert_visit_numbers_consecutive",
        "assert_visit_days_non_negative",
        "assert_milestone_dates_ascending",
        "assert_visit_count_matches_orders",
    ):
        assert name in tests, name


def edit_row(path: Path, row_id: str, column: str, value: str) -> None:
    header, *lines = path.read_text(encoding="utf-8").splitlines()
    position = header.split(",").index(column)
    for i, line in enumerate(lines):
        fields = line.split(",")  # the staging fixtures have no quoted values
        if fields[0] == row_id:
            fields[position] = value
            lines[i] = ",".join(fields)
            break
    else:
        raise AssertionError(f"no row {row_id} in {path.name}")
    path.write_text("\n".join([header, *lines]) + "\n", encoding="utf-8")


# Broken variants: (fixture, row id, column, new value, dbt test expected to fail).
BROKEN = {
    "visit before signup": (
        "stg_orders",
        "102",
        "created_at",
        "2024-01-05 12:00:00",
        "assert_visit_days_non_negative",
    ),
    "no touch at or before signup": (
        "stg_marketing_touches",
        "21",
        "touched_at",
        "2024-01-06 14:31:00",
        "not_null_dim_customers_acquisition_channel",
    ),
    "unknown channel": (
        "stg_marketing_touches",
        "12",
        "channel",
        "TikTok",
        "relationships_dim_customers_acquisition_channel__channel__ref_channels_",
    ),
    "order of an unknown customer": (
        "stg_orders",
        "205",
        "customer_id",
        "99",
        "assert_visit_count_matches_orders",
    ),
}


@pytest.mark.parametrize("case", BROKEN, ids=list(BROKEN))
def test_broken_fixture_fails_its_test(case: str, tmp_path: Path) -> None:
    table, row_id, column, value, expected = BROKEN[case]
    staging = tmp_path / "staging"
    shutil.copytree(FIXTURES, staging)
    edit_row(staging / f"{table}.csv", row_id, column, value)

    result = core_build(staging, tmp_path)
    assert not result.success
    assert expected in failed(result), failed(result)


def test_seed_42_end_to_end(tmp_path: Path) -> None:
    """Generated sources through staging and intermediate: every dbt test passes, one visit row per clean
    order, every customer has an acquisition channel, and Paid Social brings the most sign-ups."""
    raw = tmp_path / "raw"
    generate(raw, 42)
    result = dbt_build(raw, tmp_path)
    assert result.success, failed(result)
    assert rows(tmp_path, "select count(*) from intermediate.int_customer_visits") == rows(
        tmp_path, "select count(*) from staging.stg_orders"
    )
    assert rows(
        tmp_path, "select count(*) from intermediate.dim_customers where acquisition_channel is null"
    ) == [(0,)]
    assert rows(tmp_path, "select count(*) from intermediate.dim_customers") == rows(
        tmp_path, "select count(*) from staging.stg_customers"
    )
    signups = rows(
        tmp_path,
        "select acquisition_channel, count(*) from intermediate.dim_customers group by 1 order by 2 desc, 1",
    )
    assert signups[0][0] == "Paid Social", signups
    assert len(signups) == 7
