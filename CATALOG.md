# Data catalog

Generated from the dbt project's descriptions and doc blocks; do not edit by hand. Regenerate with
`uv run catalog` (CI fails when this file is out of date). All data in this project is synthetic.

Business terms are defined once under [Business terms](#business-terms); descriptions elsewhere link to them.

## Business terms

<a id="term-acquisition-channel"></a>

### acquisition channel

The channel that brought the customer in, by first touch: the channel of the customer's earliest marketing
touch at or before the signup time (`touched_at <= created_at`). Touches at the same time (source
timestamps are whole minutes, so same-minute touches tie) go to the lowest touch id. Touches after signup
never count. A customer with no touch at or before signup has no acquisition channel and fails the build. First
touch is the only attribution rule modeled.

<a id="term-active-customer"></a>

### active customer

An active customer in a quarter: a cohort customer with at least one visit in that calendar quarter. To roll
cohorts up, take one quarters_since_signup, sum cohort_size, active_customers, visits, and revenue across
cohorts (channels or cohort quarters), and divide the sums; never sum across offsets (cohort_size repeats on
every offset row and a customer can be active at several) and never average stored rates.

<a id="term-ad-spend"></a>

### ad spend

Simulated marketing spend in dollars, by channel and day, summed over campaigns.

<a id="term-channel"></a>

### channel

A canonical marketing channel, one of seven: Paid Search, Paid Social, Organic Search, Email, Referral,
In-store, Direct/Unknown. Source labels spelled many ways map to one channel through the `channel_labels`
seed; adding a channel or a label is a seed change.

<a id="term-clean-visit"></a>

### clean visit

A visit that counts: an order whose status, trimmed and lowercased, is `paid` or `complete` (not a
refund), with a total above zero, belonging to a known customer that is not a test account. Every row of
`stg_orders` is a clean visit.

<a id="term-cohort"></a>

### cohort

A signup cohort: the customers acquired by one channel whose signup date falls in one calendar quarter.
Quarters since signup count calendar quarters from the signup quarter (0) to the visit's quarter, so a
sign-up on 31 March and a visit on 1 April are one quarter apart.

<a id="term-customer"></a>

### customer

A person with a store account: an online account or an in-store email signup. A customer counts once per
email address: emails are compared trimmed and lowercased, and when two accounts share an email the
earliest created one (then the lowest id) is the customer. Test accounts are not customers.

<a id="term-milestone"></a>

### milestone

A visit milestone: the customer's nth visit, for each n in the `milestones` dbt variable (default 1, 2, 3,
5, 10). A customer reaches milestone n on the date of their nth visit. Changing the variable changes no
schema.

<a id="term-signup"></a>

### signup

A sign-up: a customer's account creation, counted once per customer in the quarter of its UTC signup date
(`dim_customers.signup_date`). A sign-up on 31 March is in the first quarter; one on 1 April, the second.

<a id="term-step-rate"></a>

### step rate

The share of customers at the previous step who reach this one: customers reaching this milestone divided by
customers reaching the milestone before it, from 0 to 1. To roll cohorts or months up, sum the customer
counts and divide the sums; never average step rates.

<a id="term-test-account"></a>

### test account

A junk customer record left by testing: an email on `@example.com`, or a first or last name `test` (any
case). Test accounts and their orders are dropped in staging.

<a id="term-utc-timestamp"></a>

### utc timestamp

Timestamp in UTC, without a time zone. Source values come in four forms (ISO 8601 with `Z` or with an
offset, `YYYY-MM-DD HH:MM:SS`, `MM/DD/YYYY HH:MM`); values without an offset are UTC.

<a id="term-visit"></a>

### visit

One purchase visit: one online order or one in-store transaction.

## Sources

### Source `raw`

The six synthetic source CSVs written by the generator (`uv run generate`) to the folder in the `raw_data_dir` variable (default `data/raw`). Every column is read as text, so the deliberate mess M1-M6 reaches staging as written; formats are described in `data/raw/README.md`.

#### `raw.ad_spend`

One row per channel label, campaign, and day of simulated ad spend.

| Column | Description |
|---|---|
| `date` | Day of the spend, `YYYY-MM-DD` or `MM/DD/YYYY` (M3). |
| `channel` | Channel label, spelled many ways (M1). |
| `campaign` | Campaign name. |
| `spend` | Simulated spend in dollars. |

#### `raw.customers`

One row per store account, including duplicate accounts (M2) and test accounts (M6).

| Column | Description |
|---|---|
| `id` | Account id; positive integer, rising with signup time. |
| `created_at` | When the account was created, in one of four timestamp forms (M3). |
| `email` | Account email; duplicates differ by case or surrounding whitespace (M2). |
| `first_name` | First name; test accounts may use `test` (M6). |
| `last_name` | Last name; test accounts may use `test` (M6). |
| `state` | Two-letter US state code. |
| `signup_location` | Where the account was created, `online` or `store`. |
| `accepts_marketing` | Marketing consent, `true` or `false`. |

#### `raw.marketing_touches`

One row per marketing touch, including touches whose email matches no customer (M4); channel and utm_source labels are spelled many ways (M1).

| Column | Description |
|---|---|
| `id` | Touch id. |
| `customer_email` | Email of the person touched. |
| `touched_at` | When the touch happened, in one of four timestamp forms (M3). |
| `channel` | Channel label, spelled many ways (M1). |
| `campaign` | Campaign name; empty for touches with no campaign. |
| `utm_source` | UTM source label, spelled many ways (M1). |
| `utm_medium` | UTM medium; one value per canonical channel. |
| `utm_campaign` | Campaign lowercased with spaces as `_`; empty when campaign is. |

#### `raw.order_lines`

One row per order line, for every order in `orders`.

| Column | Description |
|---|---|
| `id` | Order line id. |
| `order_id` | Id of the order the line belongs to. |
| `product_id` | Id of the product sold. |
| `quantity` | Units sold. |
| `unit_price` | Price per unit in dollars. |

#### `raw.orders`

One row per order, including refunds (M5), zero-total and test-account orders (M6), and orders whose customer_id matches no customer (M4).

| Column | Description |
|---|---|
| `id` | Order id; positive integer, rising with order time. |
| `customer_id` | Id of the ordering customer; some match no customer (M4). |
| `created_at` | When the order was placed, in one of four timestamp forms (M3). |
| `sales_channel` | Where the order was placed, `online` or `store`. |
| `status` | Order status, spelled inconsistently, with refunds mixed in (M5). |
| `subtotal` | Sum of the order's line quantity times unit price, in dollars. |
| `discount` | Discount in dollars. |
| `total` | Subtotal minus discount, in dollars; `0.00` on junk orders (M6). |
| `currency` | Currency code, always `USD`. |

#### `raw.products`

One row per product in the outdoor gear catalog.

| Column | Description |
|---|---|
| `id` | Product id. |
| `title` | Product name. |
| `category` | Product category (camping, climbing, footwear, apparel, packs). |
| `list_price` | List price in dollars. |

## Staging

### `stg_ad_spend`

One row per date, channel, and campaign of simulated ad spend. Fixes: dates parsed from two forms (M3), channel labels mapped to canonical channels (M1).

| Column | Description |
|---|---|
| `date` | Day of the spend. |
| `channel` | [channel](#term-channel) Mapped from the source channel label (M1). |
| `campaign` | Campaign name. |
| `spend` | Simulated spend in dollars. |

### `stg_customers`

One row per customer. [customer](#term-customer) Fixes: emails trimmed and lowercased and one row kept per email (M2), timestamps parsed to UTC (M3), test accounts dropped (M6).

| Column | Description |
|---|---|
| `id` | Customer id (the id of the account kept for the email). |
| `created_at` | Signup time. [utc timestamp](#term-utc-timestamp) |
| `email` | Email, trimmed and lowercased (M2); one row per email. |
| `first_name` | First name. |
| `last_name` | Last name. |
| `state` | Two-letter US state code. |
| `signup_location` | Where the customer signed up, `online` or `store`. |
| `accepts_marketing` | Whether the customer accepts marketing. |

### `stg_marketing_touches`

One row per marketing touch of a customer. Fixes: emails trimmed and lowercased (M2), timestamps parsed to UTC (M3), channel and utm_source labels mapped to canonical channels (M1), touches whose email matches no customer in `stg_customers` dropped (M4).

| Column | Description |
|---|---|
| `id` | Touch id. |
| `customer_email` | Email of the customer touched, trimmed and lowercased; always a customer in `stg_customers` (M4). |
| `touched_at` | Touch time. [utc timestamp](#term-utc-timestamp) |
| `channel` | [channel](#term-channel) Mapped from the source channel label (M1). |
| `campaign` | Campaign name; null for touches with no campaign. |
| `utm_source` | UTM source label, trimmed and lowercased. |
| `utm_source_channel` | [channel](#term-channel) Mapped from utm_source (M1). |
| `utm_medium` | UTM medium; one value per canonical channel. |
| `utm_campaign` | Campaign lowercased with spaces as `_`; null when campaign is. |

### `stg_order_lines`

One row per line of a clean visit; lines of orders dropped from `stg_orders` are dropped too.

| Column | Description |
|---|---|
| `id` | Order line id. |
| `order_id` | Id of the order, always an order in `stg_orders`. |
| `product_id` | Id of the product sold. |
| `quantity` | Units sold. |
| `unit_price` | Price per unit in dollars. |

### `stg_orders`

One row per clean visit. [clean visit](#term-clean-visit) Fixes: timestamps parsed to UTC (M3), orders of unknown customers dropped (M4), status trimmed and lowercased with `complete` as `paid` and refunds dropped (M5), zero-total orders and orders of test accounts dropped (M6).

| Column | Description |
|---|---|
| `id` | Order id. |
| `customer_id` | Id of the ordering customer, always a customer in `stg_customers` (M4). |
| `created_at` | Visit time. [utc timestamp](#term-utc-timestamp) |
| `sales_channel` | Where the visit happened, `online` or `store`. |
| `status` | Order status after the M5 fix; always `paid`. |
| `subtotal` | Sum of the order's line quantity times unit price, in dollars. |
| `discount` | Discount in dollars. |
| `total` | Subtotal minus discount, in dollars; always above zero (M6). |
| `currency` | Currency code (`USD`). |

### `stg_products`

One row per product in the outdoor gear catalog.

| Column | Description |
|---|---|
| `id` | Product id. |
| `title` | Product name. |
| `category` | Product category. |
| `list_price` | List price in dollars. |

## Intermediate

### `dim_customers`

One row per customer. [customer](#term-customer) Carries the signup date, the acquisition channel, and the date of each visit milestone; customers with no visits are included with every milestone date null.

| Column | Description |
|---|---|
| `customer_id` | Customer id, as in `stg_customers`. |
| `signup_date` | Date the customer signed up (UTC). |
| `signup_location` | Where the customer signed up, `online` or `store`. |
| `acquisition_channel` | [acquisition channel](#term-acquisition-channel) [channel](#term-channel) |
| `milestone_dates` | [milestone](#term-milestone) A map from each configured milestone to the date the customer reached it, null when not reached; every milestone is a key. `milestone_dates[3]` is the third-visit date. Dates never decrease as the milestone rises. |

### `int_channel_spend_daily`

One row per channel and day that has rows in `stg_ad_spend`. [ad spend](#term-ad-spend) Built by summing the day's campaigns; a channel and day with no `stg_ad_spend` rows has no row.

| Column | Description |
|---|---|
| `channel` | [channel](#term-channel) The channel the spend paid for. |
| `spend_date` | Day of the spend. |
| `ad_spend` | Spend in dollars for the channel and day, summed over campaigns; simulated. |

### `int_customer_visits`

One row per customer and visit number. [visit](#term-visit) Every row of `stg_orders` is one visit, numbered from 1 per customer in time order (visits at the same time by order id). Days are calendar days between UTC dates.

| Column | Description |
|---|---|
| `customer_id` | Id of the visiting customer. [customer](#term-customer) |
| `visit_number` | The visit's place in the customer's visits, consecutive from 1. |
| `order_id` | Id of the order that is this visit; one row per order in `stg_orders`. |
| `visit_date` | Date of the visit (UTC). |
| `order_total` | Order total in dollars. |
| `days_since_signup` | Calendar days from the customer's signup date to the visit date; never negative. |
| `days_since_previous_visit` | Calendar days from the previous visit's date to this one; 0 for visits on the same day; null on visit 1 only. |

## Marts

### `fct_customer_cohorts`

Whether customers stay: one row per acquisition channel, signup quarter, and quarters since signup, in long format, so a longer horizon adds rows, never columns. [customer](#term-customer) [cohort](#term-cohort) Offsets run from 0 (the signup quarter) to the `cohort_horizon_quarters` variable (default 7); visits after the horizon are not counted. Every channel in the `channels` seed has a row for every quarter from the first to the last quarter with a sign-up and every offset whose quarter is not after the quarter the data ends (the latest signup or visit date), with 0 customers where there were none. Every cohort is kept, including ones too young to reach later offsets. The rows for the quarter the data ends in may cover only part of that quarter, so their active_rate can read low. Reads only `dim_customers`, `int_customer_visits`, and the `channels` seed. All values simulated.

| Column | Description |
|---|---|
| `channel` | [acquisition channel](#term-acquisition-channel) [channel](#term-channel) |
| `cohort_quarter` | First day of the customers' signup quarter (UTC signup date). |
| `quarters_since_signup` | Calendar quarters from the signup quarter to this quarter: 0 for the signup quarter, up to the `cohort_horizon_quarters` variable. [cohort](#term-cohort) |
| `cohort_size` | Customers in the cohort: every customer the channel acquired in the signup quarter, the same on every offset row. [signup](#term-signup) |
| `active_customers` | [active customer](#term-active-customer) Counted once each however many visits they made; never more than cohort_size. |
| `active_rate` | active_customers / cohort_size, from 0 to 1; null when the cohort is empty. |
| `visits` | Visits by cohort customers in this quarter; 0 when none. [visit](#term-visit) |
| `visits_per_active_customer` | visits / active_customers; null when no cohort customer visited in this quarter. |
| `revenue` | Sum of the order totals of those visits, in dollars (simulated); 0.00 when none. |
| `average_order` | revenue / visits, in dollars; null when there were no visits. |
| `is_simulated` | Always true. Every value in this mart is synthetic. |

### `fct_signups_by_channel`

Where customers come from: one row per acquisition channel and quarter. [customer](#term-customer) Every channel in the `channels` seed has a row for every quarter from the first to the last quarter with a sign-up or spend, with 0 sign-ups and 0 spend where there were none. Reads only `dim_customers`, `int_channel_spend_daily`, and the `channels` seed. All values simulated.

| Column | Description |
|---|---|
| `channel` | [acquisition channel](#term-acquisition-channel) [channel](#term-channel) |
| `quarter` | First day of the quarter (UTC). |
| `signups` | New customers acquired by the channel in the quarter. [signup](#term-signup) |
| `signups_prior_quarter` | Sign-ups for the same channel in the previous quarter; 0 when it had none, null only in the first quarter of the data. |
| `signups_change` | Quarter-over-quarter change, (signups - signups_prior_quarter) / signups_prior_quarter, as a fraction (0.25 is 25% more); null when the prior quarter is null or 0. |
| `share_of_signups` | The channel's share of all sign-ups in the quarter, from 0 to 1; shares sum to 1 per quarter. Null when the quarter has no sign-ups. |
| `ad_spend` | [ad spend](#term-ad-spend) Total for the channel and quarter, in dollars; 0 for channels with no spend. |
| `cost_per_signup` | Simulated spend per sign-up, ad_spend / signups, in dollars; null when signups or ad_spend is 0. |
| `is_simulated` | Always true. Every value in this mart is synthetic. |

### `fct_visit_funnel_by_channel`

How fast customers convert: one row per acquisition channel, signup cohort month, and milestone, in long format, so a new milestone adds rows, never columns. [customer](#term-customer) [milestone](#term-milestone) Milestone 0 is the signup. Every channel in the `channels` seed has a row for every milestone of every month from the first to the last month with a sign-up or spend, with 0 customers where there were none. Every cohort is kept, including ones too young to reach later milestones. To roll months up, sum customers_reached and ad_spend, recompute step_rate from the sums, and weight avg_days_from_previous by customers_reached. Reads only `dim_customers`, `int_channel_spend_daily`, and the `channels` seed. All values simulated.

| Column | Description |
|---|---|
| `channel` | [acquisition channel](#term-acquisition-channel) [channel](#term-channel) |
| `cohort_month` | First day of the customers' signup month (UTC signup date). |
| `milestone` | 0 for the signup, else the visit number n of a milestone. [milestone](#term-milestone) |
| `previous_milestone` | The step before this milestone in sorted order: 0 (signup) for the first visit milestone; null on the signup row. |
| `customers_reached` | Customers in the cohort who reached this milestone. On the signup row, the cohort size: every customer who signed up that month. [signup](#term-signup) Never rises as the milestone rises. |
| `step_rate` | [step rate](#term-step-rate) Null on the signup row and when no customer reached the previous step. |
| `avg_days_from_previous` | Mean calendar days from the previous milestone's date (the signup date for the first visit milestone) to this milestone's date, over the customers who reached this milestone; null on the signup row and when no customer reached it. |
| `ad_spend` | [ad spend](#term-ad-spend) Total for the channel and month, in dollars, on the signup row only (0 when the channel had no spend); null on every other row, so summing the column never double counts. |
| `is_simulated` | Always true. Every value in this mart is synthetic. |

## Seeds

### `channel_labels`

Maps every channel label and UTM source label in the source data, trimmed and lowercased, to its canonical channel (M1). One row per label; staging looks labels up by `lower(trim(label))`, so a label missing here leaves the channel null and fails the staging not_null tests.

| Column | Description |
|---|---|
| `label` | A channel or UTM source label as written in the sources, trimmed and lowercased. |
| `channel` | The canonical channel the label maps to. |

### `channels`

[channel](#term-channel) One row per canonical channel.

| Column | Description |
|---|---|
| `channel` | Canonical channel name. |
