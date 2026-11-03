"""Shared loader for the mart tests: hand-made fixtures shaped like `dim_customers`,
`int_channel_spend_daily`, and `int_customer_visits` (whichever a fixture folder has) are loaded into an
`intermediate` schema, the `channels` seed into `staging`, and then one mart is built and tested on them."""

from __future__ import annotations

from pathlib import Path

import duckdb
from dbt.cli.main import dbtRunnerResult
from test_staging import FIXTURES as RAW_FIXTURES
from test_staging import dbt_build

from retail_analytics.config import DBT_DIR

INTERMEDIATE_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "intermediate"
# Column types of the intermediate models the marts read, in model column order. `milestone_dates` is read
# from the CSV as text in DuckDB map form (`{1=2024-01-03, 2=NULL}`) and cast; a fixture without the column
# (the sign-ups mart does not read it) gets it as a null map column.
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
    "int_customer_visits": {
        "customer_id": "bigint",
        "visit_number": "bigint",
        "order_id": "bigint",
        "visit_date": "date",
        "order_total": "decimal(12, 2)",
        "days_since_signup": "bigint",
        "days_since_previous_visit": "bigint",
    },
}
MILESTONE_DATES = "map(integer, date)"


def load_intermediate(intermediate_dir: Path, work: Path) -> None:
    """Load the fixtures present in `intermediate_dir` (one CSV per model in `INTERMEDIATE_TYPES`; a missing
    one is skipped) and the `channels` seed into `work/warehouse.duckdb`."""
    with duckdb.connect(str(work / "warehouse.duckdb")) as con:
        con.execute("create schema intermediate")
        con.execute("create schema staging")
        for table, types in INTERMEDIATE_TYPES.items():
            path = intermediate_dir / f"{table}.csv"
            if not path.exists():
                continue
            header = path.read_text(encoding="utf-8").splitlines()[0].split(",")
            has_milestones = table == "dim_customers" and "milestone_dates" in header
            types = {**types, "milestone_dates": "varchar"} if has_milestones else types
            columns = ", ".join(f"'{name}': '{kind}'" for name, kind in types.items())
            select = (
                f"* replace (cast(milestone_dates as {MILESTONE_DATES}) as milestone_dates)"
                if has_milestones
                else "*"
            )
            con.execute(
                f"create table intermediate.{table} as select {select} from read_csv("
                f"'{path}', header = true, columns = {{{columns}}})"
            )
            if table == "dim_customers" and not has_milestones:
                con.execute(f"alter table intermediate.{table} add column milestone_dates {MILESTONE_DATES}")
        con.execute(
            f"create table staging.channels as select * from read_csv("
            f"'{DBT_DIR / 'seeds' / 'channels.csv'}', header = true, columns = {{'channel': 'varchar'}})"
        )


def mart_build(
    intermediate_dir: Path, work: Path, model: str, extra_vars: dict | None = None
) -> dbtRunnerResult:
    """Load the intermediate fixtures, run the spend model's tests on its fixture when there is one, then
    `dbt build --select <model>` (the mart and its tests only). Returns the first failing result, else the
    mart build's."""
    load_intermediate(intermediate_dir, work)
    if not (intermediate_dir / "int_channel_spend_daily.csv").exists():
        return dbt_build(RAW_FIXTURES, work, select=(model,), extra_vars=extra_vars)
    # The spend total check compares against stg_ad_spend, which has no fixture here.
    spend_tests = dbt_build(
        RAW_FIXTURES,
        work,
        select=("int_channel_spend_daily,test_type:generic",),
        command="test",
    )
    if not spend_tests.success:
        return spend_tests
    return dbt_build(RAW_FIXTURES, work, select=(model,), extra_vars=extra_vars)
