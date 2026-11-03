"""Checks for the C-4 source generator: contract headers, volume and the 1.65 visit rate, one format
per field outside M1-M6, each mess item present, determinism, and the story signals for seed 42.
Everything is measured on the written CSVs, the way the dbt staging layer will read them."""

from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from retail_analytics import config
from retail_analytics.generator import COLUMNS, cli, generate
from retail_analytics.generator.mess import (
    CHANNEL_LABELS,
    PAID_STATUSES,
    REFUND_STATUSES,
    UTM_MEDIUM,
    UTM_SOURCE_LABELS,
)
from retail_analytics.generator.simulate import CHANNELS

GENERATOR_DIR = Path(__file__).resolve().parents[1] / "src" / "retail_analytics" / "generator"

# Contract headers, copied from docs/data-contracts.md on purpose (not imported from the generator).
CONTRACT_HEADERS = {
    "customers.csv": "id,created_at,email,first_name,last_name,state,signup_location,accepts_marketing",
    "orders.csv": "id,customer_id,created_at,sales_channel,status,subtotal,discount,total,currency",
    "order_lines.csv": "id,order_id,product_id,quantity,unit_price",
    "products.csv": "id,title,category,list_price",
    "marketing_touches.csv": (
        "id,customer_email,touched_at,channel,campaign,utm_source,utm_medium,utm_campaign"
    ),
    "ad_spend.csv": "date,channel,campaign,spend",
}

# M3 forms. Forms without an offset are UTC. Every timestamp is on a whole minute.
TIMESTAMP_FORMS = {
    "iso_utc": re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:00Z$"),
    "iso_offset": re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:00[+-]\d{2}:\d{2}$"),
    "space_utc": re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:00$"),
    "us_utc": re.compile(r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2}$"),
}
DATE_FORMS = {"iso": re.compile(r"^\d{4}-\d{2}-\d{2}$"), "us": re.compile(r"^\d{2}/\d{2}/\d{4}$")}

ID = re.compile(r"^[1-9]\d*$")
MONEY = re.compile(r"^\d+\.\d{2}$")
CLEAN_EMAIL = re.compile(r"^[a-z]+\.[a-z]+\.\d+@[a-z]+\.test$")
TEST_EMAIL = re.compile(r"^[a-z]+\d+@example\.com$")
SLUG = re.compile(r"^([a-z]+(_[a-z]+)*)?$")

# Features the fictional shop does not have.
FORBIDDEN = re.compile(
    r"loyal|reward|\bpoints?\b|\bmembers?(?:hip)?\b|check[- ]?in|punch ?card",
    re.IGNORECASE,
)

FIRST_QUARTER = (2024, 1)
LAST_DAY = datetime(2025, 12, 31, 23, 59)
FIRST_TOUCH = datetime(2023, 12, 2)  # touches start at most 30 days before 2024-01-01


def parse_ts(value: str) -> datetime:
    """Any M3 form to a naive UTC datetime."""
    if TIMESTAMP_FORMS["iso_offset"].match(value):
        sign = 1 if value[-6] == "+" else -1
        offset = timedelta(hours=int(value[-5:-3]), minutes=int(value[-2:]))
        return datetime.strptime(value[:19], "%Y-%m-%dT%H:%M:%S") - sign * offset
    for form, fmt in (
        ("iso_utc", "%Y-%m-%dT%H:%M:%SZ"),
        ("space_utc", "%Y-%m-%d %H:%M:%S"),
        ("us_utc", "%m/%d/%Y %H:%M"),
    ):
        if TIMESTAMP_FORMS[form].match(value):
            return datetime.strptime(value, fmt)
    raise ValueError(value)


def parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d" if DATE_FORMS["iso"].match(value) else "%m/%d/%Y")


def quarter(at: datetime) -> tuple[int, int]:
    return at.year, (at.month - 1) // 3 + 1


def read(out: Path, name: str) -> list[dict[str, str]]:
    with (out / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def norm(email: str) -> str:
    return email.strip().lower()


LABEL_TO_CHANNEL = {
    norm(lbl): ch for labels in (CHANNEL_LABELS, UTM_SOURCE_LABELS) for ch, ls in labels.items() for lbl in ls
}


@pytest.fixture(scope="session")
def generated(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict[str, int]]:
    path = tmp_path_factory.mktemp("seed42") / "data" / "raw"  # missing dir: generate creates it
    return path, generate(path, 42)


@pytest.fixture(scope="session")
def out(generated: tuple[Path, dict[str, int]]) -> Path:
    return generated[0]


@pytest.fixture(scope="session")
def report(generated: tuple[Path, dict[str, int]]) -> dict[str, int]:
    return generated[1]


@pytest.fixture(scope="session")
def data(out: Path) -> dict[str, list[dict[str, str]]]:
    return {name: read(out, f"{name}.csv") for name in COLUMNS}


@pytest.fixture(scope="session")
def clean(data: dict[str, list[dict[str, str]]]) -> dict:
    """The clean population per the README rule: dedupe M2, drop M6 test accounts, keep orders that are
    paid (any spelling), total > 0, and by a known non-test customer."""
    test_ids = {
        c["id"]
        for c in data["customers"]
        if c["email"].endswith("@example.com") or "test" in (c["first_name"].lower(), c["last_name"].lower())
    }
    first_by_email: dict[str, dict[str, str]] = {}
    for c in sorted(data["customers"], key=lambda c: (parse_ts(c["created_at"]), int(c["id"]))):
        if c["id"] not in test_ids:
            first_by_email.setdefault(norm(c["email"]), c)
    customers = {c["id"]: c for c in first_by_email.values()}
    visits = [
        o
        for o in data["orders"]
        if norm(o["status"]) in {"paid", "complete"}
        and float(o["total"]) > 0
        and o["customer_id"] in customers
    ]
    return {"customers": customers, "visits": visits, "test_ids": test_ids}


def test_headers_match_contract(out: Path) -> None:
    assert sorted(p.name for p in out.glob("*.csv")) == sorted(CONTRACT_HEADERS)
    for name, header in CONTRACT_HEADERS.items():
        assert (out / name).read_text(encoding="utf-8").split("\n", 1)[0] == header, name


def test_whitespace_values_are_quoted(out: Path) -> None:
    orders = (out / "orders.csv").read_bytes()
    assert b',"Paid ",' in orders and b",Paid ," not in orders
    raw = (out / "customers.csv").read_text(encoding="utf-8")
    padded = [c["email"] for c in read(out, "customers.csv") if c["email"] != c["email"].strip()]
    assert padded, "expected whitespace-padded M2 emails"
    for email in padded:
        assert f',"{email}",' in raw and f",{email}," not in raw, email


def test_files_are_utf8_with_newline_endings(out: Path) -> None:
    for name in CONTRACT_HEADERS:
        raw = (out / name).read_bytes()
        raw.decode("utf-8")
        assert b"\r" not in raw and raw.endswith(b"\n"), name


def test_volume_and_quarters(clean: dict, data: dict) -> None:
    assert len(clean["customers"]) >= 10_000
    expected = [(y, q) for y in (2024, 2025) for q in (1, 2, 3, 4)]
    signups = Counter(quarter(parse_ts(c["created_at"])) for c in clean["customers"].values())
    visits = Counter(quarter(parse_ts(o["created_at"])) for o in clean["visits"])
    assert sorted(signups) == expected
    assert sorted(visits) == expected
    for c in data["customers"]:
        assert datetime(2024, 1, 1) <= parse_ts(c["created_at"]) <= LAST_DAY
    for o in data["orders"]:
        assert datetime(2024, 1, 1) <= parse_ts(o["created_at"]) <= LAST_DAY
    for t in data["marketing_touches"]:
        assert FIRST_TOUCH <= parse_ts(t["touched_at"]) <= LAST_DAY
    for s in data["ad_spend"]:
        assert datetime(2024, 1, 1) <= parse_date(s["date"]) <= LAST_DAY


def test_visits_per_active_customer_quarter(clean: dict) -> None:
    """Pooled over all quarters: sum of visits / sum of customers with >= 1 visit that quarter."""
    per_quarter = defaultdict(set)
    for o in clean["visits"]:
        per_quarter[quarter(parse_ts(o["created_at"]))].add(o["customer_id"])
    active = sum(len(ids) for ids in per_quarter.values())
    assert len(clean["visits"]) / active == pytest.approx(1.65, abs=0.05)


def test_fixed_formats_outside_mess(data: dict) -> None:
    """Every field outside M1-M6 has exactly one format."""
    product_ids = {p["id"] for p in data["products"]}
    for c in data["customers"]:
        assert ID.match(c["id"])
        assert CLEAN_EMAIL.match(norm(c["email"])) or TEST_EMAIL.match(c["email"]), c["email"]
        assert re.fullmatch(r"[A-Z][a-z]+|test", c["first_name"]) and re.fullmatch(
            r"[A-Z][a-z]+|test", c["last_name"]
        )
        assert re.fullmatch(r"[A-Z]{2}", c["state"])
        assert c["signup_location"] in {"online", "store"}
        assert c["accepts_marketing"] in {"true", "false"}
    for o in data["orders"]:
        assert ID.match(o["id"]) and ID.match(o["customer_id"])
        assert o["sales_channel"] in {"online", "store"}
        assert all(MONEY.match(o[k]) for k in ("subtotal", "discount", "total"))
        assert round(float(o["subtotal"]) - float(o["discount"]), 2) == float(o["total"])
        assert o["currency"] == "USD"
    subtotals = defaultdict(float)
    for line in data["order_lines"]:
        assert ID.match(line["id"]) and ID.match(line["order_id"])
        assert line["product_id"] in product_ids
        assert re.fullmatch(r"[1-9]", line["quantity"]) and MONEY.match(line["unit_price"])
        subtotals[line["order_id"]] += int(line["quantity"]) * float(line["unit_price"])
    for o in data["orders"]:
        assert round(subtotals[o["id"]], 2) == float(o["subtotal"])
    categories = {"camping", "climbing", "footwear", "apparel", "packs"}
    for p in data["products"]:
        assert ID.match(p["id"]) and p["category"] in categories and MONEY.match(p["list_price"])
    for t in data["marketing_touches"]:
        assert ID.match(t["id"])
        assert CLEAN_EMAIL.match(t["customer_email"]) or re.match(
            r"^[a-z]+\.[a-z]+\.p\d+@[a-z]+\.test$", t["customer_email"]
        )
        assert t["utm_medium"] in UTM_MEDIUM.values()
        assert SLUG.match(t["utm_campaign"]) and t["utm_campaign"] == t["campaign"].lower().replace(" ", "_")
    for s in data["ad_spend"]:
        assert MONEY.match(s["spend"]) and s["campaign"]


def test_unique_ids(data: dict) -> None:
    for name, key in (("customers", "id"), ("orders", "id"), ("order_lines", "id"), ("products", "id")):
        ids = [r[key] for r in data[name]]
        assert len(ids) == len(set(ids)), name
    touch_ids = [t["id"] for t in data["marketing_touches"]]
    assert len(touch_ids) == len(set(touch_ids))


def test_m1_channel_labels(data: dict) -> None:
    for lbl in LABEL_TO_CHANNEL:
        owners = {
            ch
            for labels in (CHANNEL_LABELS, UTM_SOURCE_LABELS)
            for ch, ls in labels.items()
            if lbl in map(norm, ls)
        }
        assert len(owners) == 1, f"label {lbl!r} maps to {owners}"
    for field in ("channel", "utm_source"):
        seen = defaultdict(set)
        for t in data["marketing_touches"]:
            seen[LABEL_TO_CHANNEL[norm(t[field])]].add(t[field])
        assert sorted(seen) == sorted(CHANNELS)
        assert all(len(v) > 1 for v in seen.values()), field
    spend = defaultdict(set)
    for s in data["ad_spend"]:
        spend[LABEL_TO_CHANNEL[norm(s["channel"])]].add(s["channel"])
    assert sorted(spend) == ["Email", "Paid Search", "Paid Social"]
    assert all(len(v) > 1 for v in spend.values())


def test_m2_duplicate_customers(data: dict, clean: dict, report: dict) -> None:
    groups = Counter(norm(c["email"]) for c in data["customers"] if c["id"] not in clean["test_ids"])
    duplicates = sum(n - 1 for n in groups.values() if n > 1)
    assert duplicates == report["M2_duplicate_customers"] > 0
    exact = Counter(c["email"] for c in data["customers"])
    assert max(exact.values()) == 1, "duplicates differ by case or whitespace, never exactly"
    ordering = {o["customer_id"] for o in data["orders"]}
    dup_ids = set(c["id"] for c in data["customers"]) - set(clean["customers"]) - clean["test_ids"]
    assert len(dup_ids) == duplicates and not dup_ids & ordering
    kept = {norm(c["email"]): parse_ts(c["created_at"]) for c in clean["customers"].values()}
    for c in data["customers"]:
        if c["id"] in dup_ids:
            assert parse_ts(c["created_at"]) > kept[norm(c["email"])], c["id"]


def test_m3_timestamp_forms(data: dict) -> None:
    for name, field in (
        ("customers", "created_at"),
        ("orders", "created_at"),
        ("marketing_touches", "touched_at"),
    ):
        forms = Counter(
            next(form for form, rx in TIMESTAMP_FORMS.items() if rx.match(r[field])) for r in data[name]
        )
        assert sorted(forms) == sorted(TIMESTAMP_FORMS), name
    dates = Counter(next(f for f, rx in DATE_FORMS.items() if rx.match(s["date"])) for s in data["ad_spend"])
    assert sorted(dates) == sorted(DATE_FORMS)


def test_m4_broken_links(data: dict, report: dict) -> None:
    customer_ids = {c["id"] for c in data["customers"]}
    emails = {norm(c["email"]) for c in data["customers"]}
    orphans = [o for o in data["orders"] if o["customer_id"] not in customer_ids]
    assert len(orphans) == report["M4_orphan_orders"] > 0
    lost = [t for t in data["marketing_touches"] if norm(t["customer_email"]) not in emails]
    assert len(lost) == report["M4_orphan_touches"] > 0


def test_m5_status_and_refunds(data: dict, clean: dict, report: dict) -> None:
    statuses = Counter(o["status"] for o in data["orders"])
    assert set(statuses) == set(PAID_STATUSES) | set(REFUND_STATUSES)
    refunds = [o for o in data["orders"] if o["status"] in REFUND_STATUSES]
    assert len(refunds) == report["M5_refund_orders"] > 0
    assert all(float(o["total"]) > 0 and o["customer_id"] in clean["customers"] for o in refunds)


def test_m6_test_and_junk(data: dict, clean: dict, report: dict) -> None:
    junk = [c for c in data["customers"] if c["id"] in clean["test_ids"]]
    assert len(junk) == report["M6_test_customers"] > 0
    assert all(c["email"].endswith("@example.com") for c in junk)
    assert any(c["first_name"].lower() == "test" for c in junk)
    assert not any(c["email"].endswith("@example.com") for c in clean["customers"].values())
    zero = [o for o in data["orders"] if float(o["total"]) == 0]
    assert (
        len([o for o in zero if o["customer_id"] in clean["customers"]]) == report["M6_zero_total_orders"] > 0
    )
    assert any(o["customer_id"] in clean["test_ids"] for o in data["orders"])


def test_first_touch_at_or_before_signup(data: dict, clean: dict) -> None:
    """Every clean customer has a touch at or before signup; later pre-signup touches on other channels mean
    other attribution rules give different answers from the same data."""
    touches = defaultdict(list)
    for t in data["marketing_touches"]:
        touches[t["customer_email"]].append((parse_ts(t["touched_at"]), LABEL_TO_CHANNEL[norm(t["channel"])]))
    differs = 0
    for c in clean["customers"].values():
        signup = parse_ts(c["created_at"])
        before = sorted(x for x in touches[c["email"]] if x[0] <= signup)
        assert before, c["email"]
        assert before[0][0] < before[1][0] if len(before) > 1 else True
        if before[0][0] == signup:
            assert before[0][1] == "In-store" and c["signup_location"] == "store"
        differs += before[-1][1] != before[0][1]
    assert differs / len(clean["customers"]) > 0.3


def test_story_signals_seed_42(data: dict, clean: dict) -> None:
    first_touch = {}
    for t in sorted(data["marketing_touches"], key=lambda t: parse_ts(t["touched_at"])):
        first_touch.setdefault(t["customer_email"], LABEL_TO_CHANNEL[norm(t["channel"])])
    channel = {cid: first_touch[c["email"]] for cid, c in clean["customers"].items()}
    signups = Counter(channel.values())
    assert signups.most_common(1)[0][0] == "Paid Social"
    visits = Counter(o["customer_id"] for o in clean["visits"])
    repeat = {
        ch: sum(visits[cid] >= 2 for cid in channel if channel[cid] == ch) / signups[ch] for ch in signups
    }
    assert repeat["Referral"] > repeat["Paid Social"]
    assert repeat["Email"] > repeat["Paid Social"]


def test_deterministic_and_overwrites(out: Path, tmp_path: Path) -> None:
    target = tmp_path / "raw"
    target.mkdir()
    (target / "orders.csv").write_text("stale\n", encoding="utf-8")
    generate(target, 42)
    for name in CONTRACT_HEADERS:
        assert (target / name).read_bytes() == (out / name).read_bytes(), name


def test_other_seed_differs(out: Path, tmp_path: Path) -> None:
    generate(tmp_path, 7)
    for name in ("customers.csv", "orders.csv", "marketing_touches.csv", "ad_spend.csv"):
        assert (tmp_path / name).read_bytes() != (out / name).read_bytes(), name
    assert (tmp_path / "products.csv").read_bytes() == (out / "products.csv").read_bytes()


def test_cli_writes_to_raw_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    target = tmp_path / "raw"
    monkeypatch.setattr(config, "RAW_DATA_DIR", target)
    cli.main(["--seed", "3"])
    assert sorted(p.name for p in target.glob("*.csv")) == sorted(CONTRACT_HEADERS)


def test_cli_defaults_to_seed_42(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, out: Path) -> None:
    target = tmp_path / "raw"
    monkeypatch.setattr(config, "RAW_DATA_DIR", target)
    cli.main([])
    for name in CONTRACT_HEADERS:
        assert (target / name).read_bytes() == (out / name).read_bytes(), name


def test_no_forbidden_terms(out: Path) -> None:
    files = [*out.glob("*.csv"), *GENERATOR_DIR.glob("*.py")]
    for path in files:
        hits = FORBIDDEN.findall(path.read_text(encoding="utf-8"))
        assert not hits, f"{path.name}: {sorted(set(hits))}"
