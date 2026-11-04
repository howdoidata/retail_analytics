# data/raw

Synthetic source CSVs written by the generator (`src/retail_analytics/generator/`, story C-4).
Contents are gitignored; regenerate them rather than committing them. File shapes:
[`docs/data-contracts.md`](../../docs/data-contracts.md#source-csvs-generator-output). All data is synthetic.

```bash
uv run generate            # seed 42 (default); writes the six CSVs here, overwriting them
uv run generate --seed 7   # another seed: different, internally consistent files
uv run build               # also rewrites these files (seed 42, or --seed N) before it builds
```

The same seed gives byte-identical files on the pinned Python (3.12, `.python-version`). The data covers 2024-01-01 to 2025-12-31 (8 quarters,
each with sign-ups and visits); marketing touches can start up to 30 days before 2024-01-01.

This page is the reference the staging models (C-5) are built from: what each mess item looks like, and
how to recover the clean rows. Shares are approximate, measured on seed 42.

## File format

UTF-8, comma-delimited, header row, `\n` line endings. A value is quoted (`"..."`, inner quotes doubled)
only when it contains a comma, a quote, a line break, or leading or trailing whitespace, so the whitespace
in M2 emails and the `Paid ` status survive parsing. An empty cell means no value.

## Fields with one fixed format

Everything not listed under the mess items below has exactly one format.

| Field | Format |
|---|---|
| every `id`, `customer_id`, `order_id`, `product_id` | positive integer |
| `subtotal`, `discount`, `total`, `unit_price`, `list_price`, `spend` | dollars, two decimals (`49.00`) |
| `orders.total` | `subtotal - discount`; `subtotal` is the sum of the order's `quantity * unit_price` |
| `orders.currency` | `USD` |
| `orders.sales_channel`, `customers.signup_location` | `online` or `store` |
| `customers.accepts_marketing` | `true` or `false` |
| `customers.state` | two-letter US state code |
| `customers.first_name`, `last_name` | capitalized name (M6 test accounts may use `test`) |
| `customers.email`, `marketing_touches.customer_email` | lowercase, on a `.test` domain (except M2 and M6 below) |
| `products.category` | `camping`, `climbing`, `footwear`, `apparel`, `packs` |
| `marketing_touches.utm_medium` | one value per canonical channel (table under M1) |
| `marketing_touches.campaign` | campaign name, or empty for touches with no campaign |
| `marketing_touches.utm_campaign` | `campaign` lowercased with spaces as `_`; empty when `campaign` is |
| `ad_spend.campaign` | campaign name; one row per channel x campaign x day |

Customer ids rise with signup time and skip some numbers (closed accounts). Order ids rise with order time.

## M1: channel labels

`marketing_touches.channel` and `ad_spend.channel` use the channel labels; `marketing_touches.utm_source`
uses the source labels. About half the values use the first-listed label (for channel labels, the
canonical channel name), the rest one of the others. Every label maps to exactly one canonical channel after trimming and lowercasing, across both lists.

| Canonical channel | Channel labels | Source labels | `utm_medium` |
|---|---|---|---|
| Paid Search | `Paid Search`, `paid search`, `Google Ads`, `google_ads`, `cpc`, `SEM` | `google`, `Google`, `bing`, `google_ads` | `cpc` |
| Paid Social | `Paid Social`, `paid_social`, `fb`, `Facebook Ads`, `facebook`, `Instagram Ads` | `facebook`, `Facebook`, `fb`, `instagram`, `ig` | `paid_social` |
| Organic Search | `Organic Search`, `organic search`, `organic`, `SEO` | `google_organic`, `bing_organic`, `duckduckgo` | `organic` |
| Email | `Email`, `email`, `E-mail`, `newsletter` | `newsletter`, `Newsletter`, `email`, `mailer` | `email` |
| Referral | `Referral`, `referral`, `Referral Partner`, `ref` | `partner_blog`, `Partner Blog`, `gear_forum` | `referral` |
| In-store | `In-store`, `In Store`, `in store`, `store`, `pos` | `store`, `in_store`, `pos` | `offline` |
| Direct/Unknown | `Direct/Unknown`, `direct`, `(direct)`, `(none)`, `unknown` | `(direct)`, `(none)`, `direct` | `(none)` |

`ad_spend` covers Paid Search, Paid Social, and Email; every other channel has no spend.

Acquisition channel (first touch): the channel of the customer's earliest touch at or before signup. Every
customer has one; an In-store customer's first touch is at the signup minute. Most customers also have
later touches on other channels before signup, and touches after signup, so last-touch or multi-touch rules
give different answers from the same rows. No file stores a derived channel.

## M2: duplicate customers

About 2% extra `customers` rows: a second account for an existing customer, created later, with the same
email differing by case (`Avery.Abbott.12@inbox.test`, `AVERY.ABBOTT.12@INBOX.TEST`) or surrounding
whitespace (`" avery.abbott.12@inbox.test"`). Duplicates have no orders and no touches. Fix: trim and
lowercase the email; keep the earliest `created_at` (then lowest `id`) per email.

## M3: timestamp formats

`customers.created_at`, `orders.created_at`, and `marketing_touches.touched_at` mix four forms. Values
without an offset are UTC. Every timestamp is on a whole minute (seconds `00`), so forms that drop seconds
never reorder events.

| Form | Example | Share |
|---|---|---|
| ISO 8601, UTC | `2024-03-05T14:07:00Z` | ~50% |
| ISO 8601 with offset (`-04:00` to `-08:00`) | `2024-03-05T09:07:00-05:00` | ~20% |
| `YYYY-MM-DD HH:MM:SS`, UTC | `2024-03-05 14:07:00` | ~15% |
| `MM/DD/YYYY HH:MM`, UTC | `03/05/2024 14:07` | ~15% |

`ad_spend.date` is a date in two forms: `YYYY-MM-DD` (~80%) and `MM/DD/YYYY` (~20%).

## M4: broken record links

- About 1% extra `orders` rows whose `customer_id` matches no customer (a skipped id).
- About 3% extra `marketing_touches` rows whose `customer_email` matches no customer, even after trimming
  and lowercasing (people who never signed up).

## M5: order status

Every visit has a paid status spelled `paid` (~70%), `PAID`, `Paid ` (trailing space), or `complete`
(~10% each). Refunds are about 2.5% extra `orders` rows: their own order id, a real customer, status
`refunded`, `Refunded`, `REFUNDED`, or `refund`, a positive total, normal lines, and no link to another order.

## M6: test and junk records

- About 0.5% extra `customers` rows: test accounts on `@example.com` (for example `test12@example.com`),
  about half named `test` (first name `test` or `Test`, last name `test`, `User`, or `Account`). Each has
  1 to 3 orders (about 0.4% of orders), about half of them zero-total. No real customer uses `@example.com`.
- About 0.7% extra zero-total `orders` rows on real customers: normal lines, `discount` equal to
  `subtotal`, `total` `0.00`, a paid status.

## Clean visits

A clean visit is an order whose status, trimmed and lowercased, is `paid` or `complete` (not a refund),
with `total > 0`, belonging to a known customer that is not a test account (`@example.com`, or first or
last name `test`). Customers count once per email after the M2 fix. Seed 42 gives about 18,700 customers
and 43,600 clean visits: 1.65 visits per active customer per quarter (pooled over the 8 quarters).
