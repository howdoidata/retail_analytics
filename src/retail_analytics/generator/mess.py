"""Deliberate mess M1-M6 (see `docs/data-contracts.md`), layered on the clean world.

Mess is either a rewrite of how a value is spelled (M1 channel labels, M3 timestamp formats,
M5 status spellings) or extra rows (M2 duplicate customers, M4 orphan orders and touches,
M5 refunds, M6 test customers and zero-total orders). Clean rows are never damaged, so the
clean visits stay recoverable: paid (any spelling), total > 0, by a known non-test customer.

Every other field has exactly one format.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from retail_analytics.generator.simulate import (
    CHANNELS,
    EMAIL_DOMAINS,
    END,
    FIRST_NAMES,
    LAST_NAMES,
    STATES,
    Customer,
    Touch,
    World,
    make_order,
    random_minute,
)

# M1: every spelling each canonical channel appears under. Unambiguous after trimming and lowercasing,
# so one mapping seed covers marketing_touches.channel, utm_source, and ad_spend.channel.
CHANNEL_LABELS = {
    "Paid Search": ("Paid Search", "paid search", "Google Ads", "google_ads", "cpc", "SEM"),
    "Paid Social": ("Paid Social", "paid_social", "fb", "Facebook Ads", "facebook", "Instagram Ads"),
    "Organic Search": ("Organic Search", "organic search", "organic", "SEO"),
    "Email": ("Email", "email", "E-mail", "newsletter"),
    "Referral": ("Referral", "referral", "Referral Partner", "ref"),
    "In-store": ("In-store", "In Store", "in store", "store", "pos"),
    "Direct/Unknown": ("Direct/Unknown", "direct", "(direct)", "(none)", "unknown"),
}
UTM_SOURCE_LABELS = {
    "Paid Search": ("google", "Google", "bing", "google_ads"),
    "Paid Social": ("facebook", "Facebook", "fb", "instagram", "ig"),
    "Organic Search": ("google_organic", "bing_organic", "duckduckgo"),
    "Email": ("newsletter", "Newsletter", "email", "mailer"),
    "Referral": ("partner_blog", "Partner Blog", "gear_forum"),
    "In-store": ("store", "in_store", "pos"),
    "Direct/Unknown": ("(direct)", "(none)", "direct"),
}
# Not mess: one fixed value per channel.
UTM_MEDIUM = {
    "Paid Search": "cpc",
    "Paid Social": "paid_social",
    "Organic Search": "organic",
    "Email": "email",
    "Referral": "referral",
    "In-store": "offline",
    "Direct/Unknown": "(none)",
}

# M3: timestamp forms and their shares. Forms without an offset are UTC.
TIMESTAMP_FORMS = ("iso_utc", "iso_offset", "space_utc", "us_utc")
TIMESTAMP_WEIGHTS = (50, 20, 15, 15)
OFFSET_HOURS = (-4, -5, -6, -7, -8)
DATE_FORMS = ("iso", "us")
DATE_WEIGHTS = (80, 20)

# M5: status spellings. Clean visits carry a paid spelling; refunds are extra rows.
PAID_STATUSES = ("paid", "PAID", "Paid ", "complete")
PAID_WEIGHTS = (70, 10, 10, 10)
REFUND_STATUSES = ("refunded", "Refunded", "REFUNDED", "refund")

# Shares of extra rows.
DUPLICATE_SHARE = 0.02  # M2: of customers
TEST_CUSTOMER_SHARE = 0.005  # M6: of customers
ORPHAN_ORDER_SHARE = 0.01  # M4: of orders
ORPHAN_TOUCH_SHARE = 0.03  # M4: of touches
REFUND_SHARE = 0.025  # M5: of orders
ZERO_TOTAL_SHARE = 0.007  # M6: of orders, on real customers (test customers add more)

FIRST_CUSTOMER_ID = 100001
TEST_NUM_BASE = (
    1_000_000  # simulation numbers for extra accounts are negative: -k duplicates, below -1e6 tests
)
FIRST_ORDER_ID = 500001
FIRST_LINE_ID = 1
FIRST_TOUCH_ID = 1


@dataclass
class Tables:
    """Rows per CSV, in file order, every value already a string."""

    customers: list[list[str]]
    orders: list[list[str]]
    order_lines: list[list[str]]
    products: list[list[str]]
    marketing_touches: list[list[str]]
    ad_spend: list[list[str]]
    report: dict[str, int]  # how many rows of each mess item were injected


def label(rng: random.Random, channel: str, labels: dict[str, tuple[str, ...]]) -> str:
    """The canonical spelling about half the time, otherwise another spelling."""
    options = labels[channel]
    return options[0] if rng.random() < 0.5 else rng.choice(options[1:])


def timestamp(rng: random.Random, at: datetime) -> str:
    form = rng.choices(TIMESTAMP_FORMS, TIMESTAMP_WEIGHTS)[0]
    if form == "iso_utc":
        return at.strftime("%Y-%m-%dT%H:%M:%SZ")
    if form == "iso_offset":
        hours = rng.choice(OFFSET_HOURS)
        local = at + timedelta(hours=hours)
        return f"{local:%Y-%m-%dT%H:%M:%S}-{-hours:02d}:00"
    if form == "space_utc":
        return at.strftime("%Y-%m-%d %H:%M:%S")
    return at.strftime("%m/%d/%Y %H:%M")


def date_value(rng: random.Random, day: date) -> str:
    form = rng.choices(DATE_FORMS, DATE_WEIGHTS)[0]
    return day.strftime("%Y-%m-%d") if form == "iso" else day.strftime("%m/%d/%Y")


def money(cents: int) -> str:
    return f"{cents // 100}.{cents % 100:02d}"


def slug(text: str) -> str:
    return text.lower().replace(" ", "_")


def apply(rng: random.Random, world: World) -> Tables:
    report = {}
    customers = list(world.customers)
    real = list(world.customers)
    orders = [(order, rng.choices(PAID_STATUSES, PAID_WEIGHTS)[0]) for order in world.orders]

    # M2: a second account with the same email differing by case or whitespace; no orders, no touches.
    duplicates = []
    for k, original in enumerate(rng.sample(real, round(len(real) * DUPLICATE_SHARE)), start=1):
        created = min(original.created_at + timedelta(minutes=rng.randrange(1, 120 * 24 * 60)), END)
        duplicates.append(
            Customer(
                num=-k,
                created_at=created,
                channel=original.channel,
                first_name=original.first_name,
                last_name=original.last_name,
                email=_email_variant(rng, original.email),
                state=original.state,
                signup_location="online",
                accepts_marketing=rng.random() < 0.5,
            )
        )
    customers += duplicates
    report["M2_duplicate_customers"] = len(duplicates)

    # M6: test and junk accounts on @example.com, about half named "test", with a few orders each.
    tests = []
    for k in range(1, round(len(real) * TEST_CUSTOMER_SHARE) + 1):
        named_test = rng.random() < 0.5
        tests.append(
            Customer(
                num=-TEST_NUM_BASE - k,
                created_at=random_minute(rng, datetime(2024, 1, 1), END),
                channel="Direct/Unknown",
                first_name=rng.choice(("test", "Test")) if named_test else rng.choice(FIRST_NAMES),
                last_name=rng.choice(("test", "User", "Account")) if named_test else rng.choice(LAST_NAMES),
                email=f"{rng.choice(('test', 'qa', 'demo'))}{k}@example.com",
                state=rng.choice(STATES),
                signup_location="online",
                accepts_marketing=False,
            )
        )
    customers += tests
    report["M6_test_customers"] = len(tests)

    test_orders = 0
    for customer in tests:
        for _ in range(rng.randint(1, 3)):
            at = random_minute(rng, customer.created_at, END + timedelta(minutes=1))
            order = make_order(rng, customer, at, world.products)
            if rng.random() < 0.5:
                order.discount_cents = order.subtotal_cents
            orders.append((order, rng.choices(PAID_STATUSES, PAID_WEIGHTS)[0]))
            test_orders += 1
    report["M6_test_customer_orders"] = test_orders

    # M6: zero-total orders on real customers (fully discounted).
    by_num = {c.num: c for c in real}
    visits = list(world.orders)
    zero = 0
    for visit in rng.sample(visits, round(len(visits) * ZERO_TOTAL_SHARE)):
        customer = by_num[visit.customer_num]
        at = min(visit.created_at + timedelta(minutes=rng.randrange(1, 3 * 24 * 60)), END)
        order = make_order(rng, customer, at, world.products)
        order.discount_cents = order.subtotal_cents
        orders.append((order, rng.choices(PAID_STATUSES, PAID_WEIGHTS)[0]))
        zero += 1
    report["M6_zero_total_orders"] = zero

    # M5: refunds as their own rows after a real visit, positive total, normal lines, no link to the visit.
    refunds = 0
    for visit in rng.sample(visits, round(len(visits) * REFUND_SHARE)):
        customer = by_num[visit.customer_num]
        at = min(visit.created_at + timedelta(minutes=rng.randrange(60, 30 * 24 * 60)), END)
        order = make_order(rng, customer, at, world.products)
        order.sales_channel = visit.sales_channel
        orders.append((order, rng.choice(REFUND_STATUSES)))
        refunds += 1
    report["M5_refund_orders"] = refunds

    # Customer ids rise with signup time, leaving gaps (closed accounts) for the M4 orphan orders.
    customers.sort(key=lambda c: (c.created_at, c.email))
    ids: dict[int, int] = {}
    gaps: list[int] = []
    next_id = FIRST_CUSTOMER_ID
    for customer in customers:
        if rng.random() < 0.03:
            gaps.append(next_id)
            next_id += 1
        ids[customer.num] = next_id
        next_id += 1

    # M4: orders pointing at missing customers (closed account ids).
    orphan_orders = []
    for visit in rng.sample(visits, round(len(visits) * ORPHAN_ORDER_SHARE)):
        stand_in = by_num[visit.customer_num]
        at = random_minute(rng, datetime(2024, 1, 1), END + timedelta(minutes=1))
        order = make_order(rng, stand_in, at, world.products)
        orphan_orders.append((order, rng.choices(PAID_STATUSES, PAID_WEIGHTS)[0], rng.choice(gaps)))
    report["M4_orphan_orders"] = len(orphan_orders)

    rows = [(order, status, ids[order.customer_num]) for order, status in orders] + orphan_orders
    rows.sort(key=lambda r: (r[0].created_at, r[2], r[0].subtotal_cents))

    order_rows, line_rows = [], []
    line_id = FIRST_LINE_ID
    for offset, (order, status, customer_id) in enumerate(rows):
        order_id = FIRST_ORDER_ID + offset
        subtotal = order.subtotal_cents
        order_rows.append(
            [
                str(order_id),
                str(customer_id),
                timestamp(rng, order.created_at),
                order.sales_channel,
                status,
                money(subtotal),
                money(order.discount_cents),
                money(subtotal - order.discount_cents),
                "USD",
            ]
        )
        for product_id, quantity, price in order.lines:
            line_rows.append([str(line_id), str(order_id), str(product_id), str(quantity), money(price)])
            line_id += 1

    # M4: touches from people who never signed up (email matches no customer).
    touches = list(world.touches)
    orphan_touches = []
    for k in range(round(len(touches) * ORPHAN_TOUCH_SHARE)):
        email = f"{rng.choice(FIRST_NAMES)}.{rng.choice(LAST_NAMES)}.p{k + 1}@{rng.choice(EMAIL_DOMAINS)}"
        channel = rng.choice([c for c in CHANNELS if c != "In-store"])
        at = random_minute(rng, datetime(2024, 1, 1), END + timedelta(minutes=1))
        orphan_touches.append(Touch(email.lower(), at, channel, ""))
    touches += orphan_touches
    report["M4_orphan_touches"] = len(orphan_touches)
    touches.sort(key=lambda t: (t.touched_at, t.email, t.channel))

    touch_rows = []
    for offset, touch in enumerate(touches):
        touch_rows.append(
            [
                str(FIRST_TOUCH_ID + offset),
                touch.email,
                timestamp(rng, touch.touched_at),
                label(rng, touch.channel, CHANNEL_LABELS),
                touch.campaign,
                label(rng, touch.channel, UTM_SOURCE_LABELS),
                UTM_MEDIUM[touch.channel],
                slug(touch.campaign),
            ]
        )

    return Tables(
        customers=[
            [
                str(ids[c.num]),
                timestamp(rng, c.created_at),
                c.email,
                c.first_name,
                c.last_name,
                c.state,
                c.signup_location,
                "true" if c.accepts_marketing else "false",
            ]
            for c in customers
        ],
        orders=order_rows,
        order_lines=line_rows,
        products=[
            [str(pid), title, category, money(price)] for pid, title, category, price in world.products
        ],
        marketing_touches=touch_rows,
        ad_spend=[
            [date_value(rng, s.day), label(rng, s.channel, CHANNEL_LABELS), s.campaign, money(s.cents)]
            for s in world.spend
        ],
        report=report,
    )


def _email_variant(rng: random.Random, email: str) -> str:
    """Same address, different case or surrounding whitespace."""
    kind = rng.choice(("title", "upper", "space"))
    local, domain = email.split("@")
    if kind == "title":
        return f"{local.title()}@{domain}"
    if kind == "upper":
        return email.upper()
    return rng.choice((f" {email}", f"{email} ", f"  {email}"))
