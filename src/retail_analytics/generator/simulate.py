"""The clean world: one simulated customer population that every source file is drawn from.

Nothing here is messy. Customers sign up through one acquisition channel per quarter
(2024-01-01..2025-12-31), each with a first marketing touch at or before signup plus later
touches on other channels; they then come back for visits (orders with lines) until they churn
or the data ends. Paid channels get daily spend per campaign. `mess.py` adds M1-M6 on top.

All timestamps are naive UTC datetimes on whole minutes. Money is integer cents.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

START = datetime(2024, 1, 1)
END = datetime(2025, 12, 31, 23, 59)
QUARTERS = [(year, q) for year in (2024, 2025) for q in (1, 2, 3, 4)]

CHANNELS = (
    "Paid Search",
    "Paid Social",
    "Organic Search",
    "Email",
    "Referral",
    "In-store",
    "Direct/Unknown",
)


@dataclass(frozen=True)
class Profile:
    base: int  # sign-ups in the first quarter, before seasonality
    growth: float  # quarter-over-quarter growth in sign-ups
    p_first: float  # chance a new customer ever makes a first visit
    first_gap: float  # mean days from signup to the first visit
    gap: float  # mean days between later visits
    churn: float  # chance of never coming back after each visit
    aov: int  # typical order value, dollars
    cps: float  # simulated cost per signup, dollars (0 = no ad spend)


# Invented to give the views a story: Paid Social brings the most sign-ups and the weakest repeat;
# Referral and Email bring few sign-ups and the stickiest customers; In-store buys on day 0.
PROFILES = {
    "Paid Search": Profile(430, 0.03, 0.80, 8, 50, 0.30, 72, 32.0),
    "Paid Social": Profile(520, 0.07, 0.68, 12, 58, 0.48, 56, 18.0),
    "Organic Search": Profile(300, 0.04, 0.75, 14, 50, 0.26, 68, 0.0),
    "Email": Profile(170, 0.02, 0.86, 6, 42, 0.15, 76, 3.0),
    "Referral": Profile(120, 0.05, 0.88, 7, 40, 0.11, 84, 0.0),
    "In-store": Profile(220, 0.01, 0.97, 0, 45, 0.16, 95, 0.0),
    "Direct/Unknown": Profile(200, 0.02, 0.72, 10, 52, 0.29, 64, 0.0),
}
SEASONALITY = {1: 0.90, 2: 1.05, 3: 0.95, 4: 1.20}  # by quarter of year (Q4 holiday bump)
GAP_SCALE = 1.05  # stretches every gap between visits; tuned so visits per active customer-quarter ~1.65

# Campaigns per channel with spend or campaign-tagged touches; the holiday ones run in Q4 only.
CAMPAIGNS = {
    "Paid Search": ("Brand Search", "Tents and Shelters", "Trail Footwear"),
    "Paid Social": ("Spring Trail Sale", "Summit Season", "Holiday Gear Guide"),
    "Email": ("Weekly Trail Notes", "New Arrivals", "Holiday Gift Picks"),
    "Referral": ("Partner Gear Reviews",),
}
HOLIDAY_CAMPAIGNS = ("Holiday Gear Guide", "Holiday Gift Picks")
SPEND_CHANNELS = tuple(c for c in CHANNELS if PROFILES[c].cps > 0)

PRODUCTS = (
    # title, category, list price in dollars
    ("Ridgeline 2-Person Tent", "camping", 249.00),
    ("Basecamp 4-Person Tent", "camping", 389.00),
    ("Featherlite Sleeping Bag 20F", "camping", 179.00),
    ("Valley Sleeping Bag 40F", "camping", 89.00),
    ("Insulated Sleeping Pad", "camping", 119.00),
    ("Trail Camp Stove", "camping", 64.00),
    ("Titanium Cook Pot", "camping", 42.00),
    ("Camp Headlamp 350", "camping", 34.00),
    ("Folding Camp Chair", "camping", 49.00),
    ("Water Filter Bottle", "camping", 39.00),
    ("Dynamic Rope 60m", "climbing", 199.00),
    ("Alpine Harness", "climbing", 74.00),
    ("Locking Carabiner", "climbing", 14.00),
    ("Quickdraw Set of 6", "climbing", 109.00),
    ("Climbing Helmet", "climbing", 69.00),
    ("Chalk Bag", "climbing", 22.00),
    ("Bouldering Crash Pad", "climbing", 179.00),
    ("Belay Device", "climbing", 29.00),
    ("Trail Runner Shoe", "footwear", 129.00),
    ("Waterproof Hiking Boot", "footwear", 179.00),
    ("Approach Shoe", "footwear", 139.00),
    ("Camp Sandal", "footwear", 59.00),
    ("Merino Hiking Sock", "footwear", 19.00),
    ("Gaiter Pair", "footwear", 32.00),
    ("Rain Shell Jacket", "apparel", 169.00),
    ("Down Puffy Jacket", "apparel", 219.00),
    ("Fleece Pullover", "apparel", 79.00),
    ("Hiking Pant", "apparel", 84.00),
    ("Sun Hoodie", "apparel", 54.00),
    ("Merino Base Layer Top", "apparel", 89.00),
    ("Trail Cap", "apparel", 24.00),
    ("Wool Beanie", "apparel", 26.00),
    ("Daypack 22L", "packs", 89.00),
    ("Trekking Pack 55L", "packs", 239.00),
    ("Hydration Pack 12L", "packs", 79.00),
    ("Hip Pack", "packs", 39.00),
    ("Dry Bag 10L", "packs", 24.00),
    ("Pack Rain Cover", "packs", 29.00),
)
FIRST_PRODUCT_ID = 101

FIRST_NAMES = (
    "Avery", "Blake", "Camila", "Dario", "Elena", "Felix", "Grace", "Hana", "Isaac", "Jonah",
    "Keira", "Liam", "Maya", "Nora", "Omar", "Priya", "Quinn", "Rosa", "Samir", "Tessa",
    "Uma", "Victor", "Wren", "Xavier", "Yara", "Zane", "Alma", "Bruno", "Clara", "Dmitri",
    "Esme", "Finn", "Greta", "Hugo", "Ines", "Jasper", "Kofi", "Lena", "Mateo", "Nia",
)  # fmt: skip
LAST_NAMES = (
    "Abbott", "Bennett", "Castillo", "Dalton", "Ellis", "Fischer", "Garcia", "Hayes", "Ibarra",
    "Jensen", "Kato", "Lindqvist", "Morales", "Nakamura", "Okafor", "Patel", "Quintero", "Reyes",
    "Sorensen", "Tanaka", "Underwood", "Varga", "Whitaker", "Xu", "Yilmaz", "Zimmerman", "Alvarez",
    "Brooks", "Chen", "Dubois", "Eriksen", "Flores", "Gupta", "Holm", "Iverson", "Kowalski",
)  # fmt: skip
EMAIL_DOMAINS = ("trailmail.test", "inbox.test", "postbox.test", "mailhub.test")
# The store's home state comes first and carries most customers.
STATES = ("CO", "UT", "WY", "NM", "AZ", "CA", "WA", "OR", "TX", "NY", "IL", "MN")
STATE_WEIGHTS = (40, 8, 4, 5, 5, 9, 6, 5, 6, 5, 4, 3)


@dataclass
class Customer:
    num: int  # simulation number; unique, also used in the email
    created_at: datetime
    channel: str  # acquisition channel (first touch); never written to a CSV
    first_name: str
    last_name: str
    email: str
    state: str
    signup_location: str  # online / store
    accepts_marketing: bool


@dataclass
class Order:
    customer_num: int
    created_at: datetime
    sales_channel: str  # online / store
    lines: list[tuple[int, int, int]]  # (product_id, quantity, unit price in cents)
    discount_cents: int = 0

    @property
    def subtotal_cents(self) -> int:
        return sum(quantity * price for _, quantity, price in self.lines)


@dataclass
class Touch:
    email: str
    touched_at: datetime
    channel: str  # canonical; mess.py rewrites the label
    campaign: str  # "" when the touch carries no campaign


@dataclass
class Spend:
    day: date
    channel: str
    campaign: str
    cents: int


@dataclass
class World:
    products: list[tuple[int, str, str, int]]  # (id, title, category, list price in cents)
    customers: list[Customer] = field(default_factory=list)
    orders: list[Order] = field(default_factory=list)
    touches: list[Touch] = field(default_factory=list)
    spend: list[Spend] = field(default_factory=list)


def quarter_bounds(year: int, quarter: int) -> tuple[datetime, datetime]:
    """First minute of the quarter and first minute of the next one."""
    start = datetime(year, 3 * quarter - 2, 1)
    end = datetime(year + 1, 1, 1) if quarter == 4 else datetime(year, 3 * quarter + 1, 1)
    return start, end


def random_minute(rng: random.Random, start: datetime, end: datetime) -> datetime:
    """A whole minute in [start, end)."""
    minutes = int((end - start).total_seconds() // 60)
    return start + timedelta(minutes=rng.randrange(minutes))


def daytime(rng: random.Random, day: datetime) -> datetime:
    """A whole minute on the given day between 14:00 and 03:59 UTC (shop hours across US zones)."""
    midnight = day.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight + timedelta(minutes=14 * 60 + rng.randrange(14 * 60))


def simulate(rng: random.Random) -> World:
    products = [
        (FIRST_PRODUCT_ID + i, title, category, round(price * 100))
        for i, (title, category, price) in enumerate(PRODUCTS)
    ]
    world = World(products=products)
    signups: dict[tuple[str, int, int], int] = {}

    num = 0
    for index, (year, quarter) in enumerate(QUARTERS):
        q_start, q_end = quarter_bounds(year, quarter)
        for channel in CHANNELS:
            p = PROFILES[channel]
            expected = p.base * (1 + p.growth) ** index * SEASONALITY[quarter]
            count = max(1, round(expected * rng.uniform(0.93, 1.07)))
            signups[(channel, year, quarter)] = count
            for _ in range(count):
                num += 1
                customer = _customer(rng, num, channel, random_minute(rng, q_start, q_end))
                world.customers.append(customer)
                world.touches.extend(_touches(rng, customer))
                world.orders.extend(_visits(rng, customer, products))

    world.spend = _spend(rng, signups)
    return world


def _customer(rng: random.Random, num: int, channel: str, created_at: datetime) -> Customer:
    first = rng.choice(FIRST_NAMES)
    last = rng.choice(LAST_NAMES)
    email = f"{first}.{last}.{num}@{rng.choice(EMAIL_DOMAINS)}".lower()
    marketing_rate = 0.9 if channel == "Email" else 0.55
    return Customer(
        num=num,
        created_at=created_at,
        channel=channel,
        first_name=first,
        last_name=last,
        email=email,
        state=rng.choices(STATES, STATE_WEIGHTS)[0],
        signup_location="store" if channel == "In-store" else "online",
        accepts_marketing=rng.random() < marketing_rate,
    )


def active_campaigns(channel: str, day: date) -> tuple[str, ...]:
    campaigns = CAMPAIGNS.get(channel, ())
    if day.month < 10:
        campaigns = tuple(c for c in campaigns if c not in HOLIDAY_CAMPAIGNS)
    return campaigns


def _touch(rng: random.Random, email: str, at: datetime, channel: str) -> Touch:
    campaigns = active_campaigns(channel, at.date())
    return Touch(email, at, channel, rng.choice(campaigns) if campaigns else "")


def _touches(rng: random.Random, customer: Customer) -> list[Touch]:
    """First touch on the acquisition channel at or before signup, then later touches on other channels.

    Pre-signup extras sit strictly between the first touch and signup, so first touch stays unambiguous
    while last-touch or multi-touch rules can give a different channel.
    """
    signup = customer.created_at
    others = [c for c in CHANNELS if c not in (customer.channel, "In-store")]
    if customer.channel == "In-store":
        touches = [_touch(rng, customer.email, signup, "In-store")]
    else:
        first = signup - timedelta(minutes=1 + rng.randrange(30 * 24 * 60))
        touches = [_touch(rng, customer.email, first, customer.channel)]
        window = int((signup - first).total_seconds() // 60)  # minutes after the first touch, to signup
        extras = rng.choices((0, 1, 2, 3), (30, 35, 22, 13))[0] if window > 1 else 0
        for _ in range(extras):
            at = first + timedelta(minutes=1 + rng.randrange(window - 1))  # strictly before signup
            touches.append(_touch(rng, customer.email, at, rng.choice(others)))
    for _ in range(rng.choices((0, 1, 2, 3), (40, 30, 20, 10))[0]):
        if signup >= END:
            break
        at = random_minute(rng, signup + timedelta(minutes=1), END + timedelta(minutes=1))
        touches.append(_touch(rng, customer.email, at, rng.choice(("Email", "Email", *others))))
    return touches


def _basket(
    rng: random.Random, products: list[tuple[int, str, str, int]], aov: int
) -> list[tuple[int, int, int]]:
    weights = [1 / (1 + 2 * abs(price / 100 - aov) / aov) for _, _, _, price in products]
    lines: list[tuple[int, int, int]] = []
    used: list[int] = []
    for _ in range(rng.choices((1, 2, 3), (60, 30, 10))[0]):
        product_id, _, _, price = rng.choices(products, weights)[0]
        if product_id in used:
            continue
        used.append(product_id)
        lines.append((product_id, rng.choices((1, 2), (85, 15))[0], price))
    return lines


def make_order(
    rng: random.Random,
    customer: Customer,
    at: datetime,
    products: list[tuple[int, str, str, int]],
) -> Order:
    store_share = 0.8 if customer.channel == "In-store" else 0.12
    order = Order(
        customer_num=customer.num,
        created_at=at,
        sales_channel="store" if rng.random() < store_share else "online",
        lines=_basket(rng, products, PROFILES[customer.channel].aov),
    )
    if rng.random() < 0.2:
        order.discount_cents = order.subtotal_cents * rng.choice((10, 15, 20)) // 100
    return order


def _visits(rng: random.Random, customer: Customer, products: list[tuple[int, str, str, int]]) -> list[Order]:
    p = PROFILES[customer.channel]
    if rng.random() >= p.p_first:
        return []
    if p.first_gap == 0:
        at = customer.created_at + timedelta(minutes=2 + rng.randrange(20))
    else:
        days = rng.expovariate(1 / p.first_gap)
        at = daytime(rng, customer.created_at + timedelta(days=max(days, 0.5)))
    orders: list[Order] = []
    while at <= END:
        orders.append(make_order(rng, customer, at, products))
        if rng.random() < p.churn:
            break
        days = rng.expovariate(1 / (p.gap * GAP_SCALE))
        at = daytime(rng, at + timedelta(days=max(days, 1)))
    return orders


def _spend(rng: random.Random, signups: dict[tuple[str, int, int], int]) -> list[Spend]:
    """Daily spend per active campaign; each quarter totals roughly cost per signup x sign-ups."""
    rows: list[Spend] = []
    for year, quarter in QUARTERS:
        q_start, q_end = quarter_bounds(year, quarter)
        days = [q_start.date() + timedelta(days=i) for i in range((q_end - q_start).days)]
        for channel in SPEND_CHANNELS:
            budget = PROFILES[channel].cps * signups[(channel, year, quarter)] * 100 / len(days)
            for day in days:
                campaigns = active_campaigns(channel, day)
                for campaign in campaigns:
                    cents = round(budget / len(campaigns) * rng.uniform(0.75, 1.25))
                    rows.append(Spend(day, channel, campaign, cents))
    return rows
