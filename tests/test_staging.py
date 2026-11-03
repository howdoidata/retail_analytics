"""Checks for the C-5 staging models: built on hand-made fixtures (`tests/fixtures/raw/`) each mess form is
fixed or dropped exactly as `data/raw/README.md` says, a broken fixture fails its dbt test, every node is
described, and on seed 42 every dbt test passes with about 1.65 clean visits per active customer-quarter."""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest
from dbt.cli.main import dbtRunner, dbtRunnerResult

from retail_analytics.config import DBT_DIR
from retail_analytics.generator import generate

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "raw"
STAGING_MODELS = (
    "stg_customers",
    "stg_orders",
    "stg_order_lines",
    "stg_products",
    "stg_marketing_touches",
    "stg_ad_spend",
)
SEEDS = ("channels", "channel_labels")


@contextmanager
def env(name: str, value: str) -> Iterator[None]:
    old = os.environ.get(name)
    os.environ[name] = value
    try:
        yield
    finally:
        if old is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = old


def dbt_build(
    raw_dir: Path, work: Path, select: tuple[str, ...] = (), extra_vars: dict | None = None
) -> dbtRunnerResult:
    """`dbt build` on `raw_dir` into `work/warehouse.duckdb`: the whole project, or only `select`."""
    args = [
        "build",
        "--project-dir", str(DBT_DIR),
        "--profiles-dir", str(DBT_DIR),
        "--target-path", str(work / "target"),
        "--log-path", str(work / "logs"),
        "--vars", json.dumps({"raw_data_dir": str(raw_dir), **(extra_vars or {})}),
    ]  # fmt: skip
    if select:
        args += ["--select", *select]
    with env("RETAIL_DUCKDB_PATH", str(work / "warehouse.duckdb")):
        return dbtRunner().invoke(args)


def failed(result: dbtRunnerResult) -> set[str]:
    if result.result is None:  # dbt raised before running anything
        return {f"dbt raised: {result.exception!r}"}
    return {r.node.name for r in result.result if str(r.status) in {"fail", "error"}}


def rows(work: Path, sql: str) -> list[tuple]:
    with duckdb.connect(str(work / "warehouse.duckdb")) as con:
        return con.execute(sql).fetchall()


def visits_per_active_customer_quarter(work: Path) -> float:
    """Pooled over all quarters: clean visits / customers with >= 1 visit that quarter."""
    [(ratio,)] = rows(
        work,
        "select count(*) / count(distinct (customer_id, date_trunc('quarter', created_at))) "
        "from staging.stg_orders",
    )
    return float(ratio)


@pytest.fixture(scope="module")
def fixture_build(tmp_path_factory: pytest.TempPathFactory) -> Path:
    work = tmp_path_factory.mktemp("staging_fixtures")
    result = dbt_build(FIXTURES, work)
    assert result.success, failed(result)
    return work


CLEAN_CUSTOMERS = [
    (1, datetime(2024, 1, 5, 10, 0), "ana.reyes.1@inbox.test", "Ana", "Reyes", "CO", "online", True),
    (2, datetime(2024, 1, 6, 14, 30), "ben.cole.2@mail.test", "Ben", "Cole", "UT", "store", False),
    (3, datetime(2024, 2, 1, 8, 15), "cara.diaz.3@inbox.test", "Cara", "Diaz", "WA", "online", True),
    (4, datetime(2024, 2, 10, 17, 45), "dev.ng.4@mail.test", "Dev", "Ng", "OR", "online", False),
    (9, datetime(2024, 3, 10, 0, 0), "eve.fox.9@inbox.test", "Eve", "Fox", "ID", "store", False),
    (13, datetime(2024, 4, 1, 4, 0), "hal.ito.13@mail.test", "Hal", "Ito", None, "store", True),
]


def test_customers_m2_m3_m6(fixture_build: Path) -> None:
    """M2: emails trimmed + lowercased, earliest created_at (then lowest id) kept per email; M3: four forms
    to UTC; M6: test accounts dropped; empty strings to null."""
    assert rows(fixture_build, "select * from staging.stg_customers order by id") == CLEAN_CUSTOMERS


def test_timestamps_are_utc_in_any_session_time_zone(fixture_build: Path) -> None:
    """M3: the compiled model gives the same UTC values when the session is not on UTC (CI runs on UTC)."""
    compiled = fixture_build / "target" / "compiled" / "retail_analytics" / "models" / "staging"
    sql = (compiled / "stg_customers.sql").read_text(encoding="utf-8")
    with duckdb.connect() as con:
        con.execute("set TimeZone = 'America/Denver'")
        assert con.execute(f"select * from ({sql}) order by id").fetchall() == CLEAN_CUSTOMERS


def test_orders_are_clean_visits(fixture_build: Path) -> None:
    """M3 to UTC; M4 orphan dropped; M5 status fixed, refunds dropped; M6 test-account and zero-total
    orders dropped."""
    assert rows(fixture_build, "select * from staging.stg_orders order by id") == [
        (101, 1, datetime(2024, 1, 10, 15, 0), "online", "paid", *map(Decimal, ("100", "0", "100")), "USD"),
        (102, 1, datetime(2024, 2, 11, 10, 0), "store", "paid", *map(Decimal, ("50", "5", "45")), "USD"),
        (103, 2, datetime(2024, 2, 12, 9, 5), "online", "paid", *map(Decimal, ("80", "0", "80")), "USD"),
        (104, 3, datetime(2024, 2, 13, 14, 0), "store", "paid", *map(Decimal, ("30", "0", "30")), "USD"),
        (114, 9, datetime(2024, 3, 12, 0, 0), "online", "paid", *map(Decimal, ("25.5", "0", "25.5")), "USD"),
        (115, 13, datetime(2024, 4, 2, 0, 0), "store", "paid", *map(Decimal, ("130", "0", "130")), "USD"),
    ]


def test_order_lines_follow_orders(fixture_build: Path) -> None:
    assert rows(fixture_build, "select * from staging.stg_order_lines order by id") == [
        (1001, 101, 1, 2, Decimal("50.00")),
        (1002, 102, 2, 1, Decimal("50.00")),
        (1003, 103, 3, 1, Decimal("80.00")),
        (1004, 104, 2, 1, Decimal("30.00")),
        (1014, 114, 3, 1, Decimal("25.50")),
        (1015, 115, 1, 1, Decimal("50.00")),
        (1016, 115, 3, 1, Decimal("80.00")),
    ]


def test_products_typed(fixture_build: Path) -> None:
    assert rows(fixture_build, "select * from staging.stg_products order by id") == [
        (1, "Ridgeline 2-Person Tent", "camping", Decimal("50.00")),
        (2, "Approach Shoe, Low", "footwear", Decimal("50.00")),
        (3, "Summit 40L Pack", "packs", Decimal("80.00")),
    ]


def test_marketing_touches_m1_m4(fixture_build: Path) -> None:
    """M1: channel and utm_source labels to canonical channels; M2: email normalized; M3: UTC; M4: touches
    of no customer (and of a dropped test account) dropped."""
    assert rows(fixture_build, "select * from staging.stg_marketing_touches order by id") == [
        (1, "ana.reyes.1@inbox.test", datetime(2024, 1, 1, 10, 0), "Paid Social", "Winter Sale",
         "facebook", "Paid Social", "paid_social", "winter_sale"),
        (2, "ana.reyes.1@inbox.test", datetime(2024, 1, 4, 9, 0), "Paid Search", "Trail Search",
         "google", "Paid Search", "cpc", "trail_search"),
        (3, "ben.cole.2@mail.test", datetime(2024, 1, 6, 14, 30), "In-store", None,
         "in_store", "In-store", "offline", None),
        (4, "cara.diaz.3@inbox.test", datetime(2024, 1, 20, 16, 0), "Organic Search", None,
         "duckduckgo", "Organic Search", "organic", None),
        (5, "dev.ng.4@mail.test", datetime(2024, 2, 1, 0, 0), "Email", "Spring Letter",
         "newsletter", "Email", "email", "spring_letter"),
        (6, "eve.fox.9@inbox.test", datetime(2024, 3, 1, 18, 0), "Referral", "Gear Guide",
         "partner blog", "Referral", "referral", "gear_guide"),
        (7, "hal.ito.13@mail.test", datetime(2024, 3, 30, 22, 0), "Direct/Unknown", None,
         "(none)", "Direct/Unknown", "(none)", None),
    ]  # fmt: skip


def test_ad_spend_m1_m3(fixture_build: Path) -> None:
    assert rows(fixture_build, "select * from staging.stg_ad_spend order by date, channel") == [
        (date(2024, 1, 1), "Email", "Spring Letter", Decimal("15.00")),
        (date(2024, 1, 1), "Paid Search", "Trail Search", Decimal("120.00")),
        (date(2024, 1, 1), "Paid Social", "Winter Sale", Decimal("200.00")),
        (date(2024, 1, 2), "Paid Search", "Trail Search", Decimal("80.50")),
    ]


def test_channel_seed_covers_every_canonical_channel(fixture_build: Path) -> None:
    assert rows(fixture_build, "select distinct channel from staging.channel_labels order by 1") == rows(
        fixture_build, "select channel from staging.channels order by 1"
    )
    assert len(rows(fixture_build, "select * from staging.channels")) == 7


def test_every_node_is_described(fixture_build: Path) -> None:
    """Every staging model, seed, and source, and every column of each, has a description, and the
    documented columns are exactly the built (or source) columns. Later layers: their own test files."""
    manifest = json.loads((fixture_build / "target" / "manifest.json").read_text(encoding="utf-8"))
    nodes = [
        n
        for n in manifest["nodes"].values()
        if n["resource_type"] == "seed" or (n["resource_type"] == "model" and n["fqn"][1] == "staging")
    ]
    sources = list(manifest["sources"].values())
    assert sorted(n["name"] for n in nodes) == sorted(STAGING_MODELS + SEEDS)
    assert len(sources) == 6
    for node in nodes + sources:
        assert node["description"].strip(), node["unique_id"]
        for column in node["columns"].values():
            assert column["description"].strip(), f"{node['unique_id']}.{column['name']}"
    for node in nodes:
        built = rows(
            fixture_build,
            f"select column_name from information_schema.columns "
            f"where table_schema = 'staging' and table_name = '{node['name']}' order by ordinal_position",
        )
        assert list(node["columns"]) == [c for (c,) in built], node["name"]
    for source in sources:
        header = (FIXTURES / f"{source['name']}.csv").read_text(encoding="utf-8").split("\n", 1)[0]
        assert ",".join(source["columns"]) == header, source["name"]


def test_mess_tests_exist(fixture_build: Path) -> None:
    """At least one dbt test per mess item, plus unique + not_null on every staging model's grain."""
    manifest = json.loads((fixture_build / "target" / "manifest.json").read_text(encoding="utf-8"))
    tests = {n["name"] for n in manifest["nodes"].values() if n["resource_type"] == "test"}
    for name in (
        "not_null_stg_marketing_touches_channel",  # M1
        "not_null_stg_marketing_touches_utm_source_channel",  # M1
        "not_null_stg_ad_spend_channel",  # M1
        "assert_channel_labels_normalized",  # M1
        "unique_stg_customers_email",  # M2
        "assert_raw_timestamps_parse",  # M3
        "not_null_stg_orders_created_at",  # M3
        "relationships_stg_orders_customer_id__id__ref_stg_customers_",  # M4
        "relationships_stg_marketing_touches_customer_email__email__ref_stg_customers_",  # M4
        "accepted_values_stg_orders_status__paid",  # M5
        "assert_stg_customers_no_test_accounts",  # M6
        "assert_stg_orders_total_positive",  # M6
        "unique_combination_stg_ad_spend_date__channel__campaign",  # grain
    ):
        assert name in tests, name
    for model in (m for m in STAGING_MODELS if m != "stg_ad_spend"):  # grain tested by unique_combination
        assert {f"unique_{model}_id", f"not_null_{model}_id"} <= tests, model


# Broken variants: (file, column, new value for the first data row, dbt test expected to fail).
BROKEN = {
    "unknown channel label": (
        "marketing_touches",
        "channel",
        "tiktok",
        "not_null_stg_marketing_touches_channel",
    ),
    "unknown utm_source": (
        "marketing_touches",
        "utm_source",
        "myspace",
        "not_null_stg_marketing_touches_utm_source_channel",
    ),
    "unknown ad_spend label": ("ad_spend", "channel", "radio", "not_null_stg_ad_spend_channel"),
    "unparseable timestamp": ("customers", "created_at", "2024/01/05 10:00", "assert_raw_timestamps_parse"),
    "unparseable date": ("ad_spend", "date", "Jan 1 2024", "assert_raw_timestamps_parse"),
    "unknown status": ("orders", "status", "shipped", "accepted_values_stg_orders_status__paid"),
    "negative total": ("orders", "total", "-5.00", "assert_stg_orders_total_positive"),
    "missing email": ("customers", "email", "", "not_null_stg_customers_email"),
    "unknown product": (
        "order_lines",
        "product_id",
        "999",
        "relationships_stg_order_lines_product_id__id__ref_stg_products_",
    ),
}


@pytest.mark.parametrize("case", BROKEN, ids=list(BROKEN))
def test_broken_fixture_fails_its_test(case: str, tmp_path: Path) -> None:
    name, column, value, expected = BROKEN[case]
    raw = tmp_path / "raw"
    shutil.copytree(FIXTURES, raw)
    path = raw / f"{name}.csv"
    header, *lines = path.read_text(encoding="utf-8").splitlines()
    position = header.split(",").index(column)
    fields = lines[0].split(",")  # the first data row of each fixture has no quoted values
    fields[position] = value
    lines[0] = ",".join(fields)
    path.write_text("\n".join([header, *lines]) + "\n", encoding="utf-8")

    result = dbt_build(raw, tmp_path)
    assert not result.success
    assert expected in failed(result), failed(result)


def test_duplicate_ad_spend_key_fails_grain_test(tmp_path: Path) -> None:
    """Two labels of one channel on the same date and campaign collide after M1 mapping."""
    raw = tmp_path / "raw"
    shutil.copytree(FIXTURES, raw)
    with (raw / "ad_spend.csv").open("a", encoding="utf-8") as f:
        f.write("2024-01-01,cpc,Trail Search,5.00\n")  # same key as `2024-01-01,Paid Search,Trail Search`
    result = dbt_build(raw, tmp_path)
    assert not result.success
    assert "unique_combination_stg_ad_spend_date__channel__campaign" in failed(result), failed(result)


def test_seed_42_end_to_end(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    generate(raw, 42)
    result = dbt_build(raw, tmp_path)
    assert result.success, failed(result)
    assert visits_per_active_customer_quarter(tmp_path) == pytest.approx(1.65, abs=0.05)
