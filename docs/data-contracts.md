# Flagship data contracts

The shapes the generator, dbt models, catalog, dashboard, and README build against. Changing anything here is a spec change (bmad-spec update), not a code change.

## The question

Which channels bring customers who keep coming back? Answered by three views, one mart each:

1. **Where customers come from:** sign-ups by channel and quarter, with quarter-over-quarter change.
2. **How fast they convert:** visit funnel by channel: signup → 1st → 2nd → 3rd → 5th → 10th visit, with customers reaching each step, the share that moves on, and average days between steps.
3. **Whether they stay:** cohorts by signup quarter and channel: share active in each later quarter, visits per customer, average order.

Final copy wording is chosen in E-1.

## Refactor principle

Each report type is one parameterized model. Periods, milestones, and cohort offsets are settings (dbt variables or seeds), never copies of a query per period.

- **Customer:** a person with a store account (online account or in-store email signup).
- **Visit:** one purchase visit: one online order or one in-store transaction.
- **Acquisition channel:** first-touch: the channel of the customer's earliest marketing touch at or before signup.

## Volume

At least 2 years of history, at least 10,000 customers, averaging 1.65 visits per active customer per quarter (visits / customers with at least 1 visit that quarter; same measure as `visits_per_active_customer`). Deterministic from a seed (default 42). All values synthetic.

## Source CSVs (generator output)

Path `data/raw/<file>.csv`. Shaped like an online store export plus marketing data. UTF-8, comma-delimited, quoted where needed.

| File | Grain | Columns |
|---|---|---|
| `customers.csv` | customer | id, created_at, email, first_name, last_name, state, signup_location (online / store), accepts_marketing |
| `orders.csv` | visit | id, customer_id, created_at, sales_channel (online / store), status, subtotal, discount, total, currency |
| `order_lines.csv` | order line | id, order_id, product_id, quantity, unit_price |
| `products.csv` | product | id, title, category, list_price |
| `marketing_touches.csv` | touch | id, customer_email, touched_at, channel, campaign, utm_source, utm_medium, utm_campaign |
| `ad_spend.csv` | channel × campaign × day | date, channel, campaign, spend |

Product categories are outdoor gear (e.g. camping, climbing, footwear, apparel, packs). No points or rewards fields anywhere.

## Deliberate mess

Each item is injected by the generator, fixed in dbt staging, and covered by at least one dbt test. Chapter 1 shows them; Chapter 2 shows their fixes.

| Id | Mess | Where |
|---|---|---|
| M1 | Channel labels spelled many ways (`fb`, `Facebook Ads`, `facebook`, `Paid Social`) | marketing_touches.channel, utm_source, ad_spend.channel |
| M2 | Duplicate customers: same email differing by case or whitespace | customers |
| M3 | Mixed date formats and time zones (ISO 8601, `MM/DD/YYYY`, with and without offset) | all timestamp fields |
| M4 | Broken record links: orders pointing at missing customers; touches whose email matches no customer | orders.customer_id, marketing_touches.customer_email |
| M5 | Order status spelled inconsistently (`paid`, `PAID`, `Paid `, `complete`) and refunds mixed in | orders.status |
| M6 | Test and junk records (`@example.com`, name `test`, zero-total orders) | customers, orders |

## Channel taxonomy

Canonical channels: Paid Search, Paid Social, Organic Search, Email, Referral, In-store, Direct/Unknown. Mapping lives in a dbt seed; adding a channel is a seed change.

## Model layers

Built in layers so new grains, milestones, and attribution rules are added on top without rewrites.

| Layer | Model | Grain |
|---|---|---|
| Staging | `stg_<file>` | one row per clean source record (mess M1–M6 fixed) |
| Intermediate | `int_customer_visits` | customer × visit number (visit date, days since signup, days since previous visit) |
| Dimension | `dim_customers` | customer (signup date, acquisition channel, visit milestone dates) |
| Mart | `fct_signups_by_channel` | **channel × quarter** |
| Mart | `fct_visit_funnel_by_channel` | **channel × signup cohort month × milestone** |
| Mart | `fct_customer_cohorts` | **channel × signup quarter × quarters since signup** |

Milestones are a dbt variable, default `[1, 2, 3, 5, 10]`; cohort horizon is a variable, default 7 quarters after signup. Changing either changes no schema. Marts read only the dimension and intermediate layers, so each can be built against fixtures of those layers.

## Sign-ups mart

`fct_signups_by_channel`. Unique key (channel, quarter).

| Column | Type | Meaning |
|---|---|---|
| channel | text | Canonical acquisition channel |
| quarter | date | First day of the quarter |
| signups | int | New customers in the quarter |
| signups_prior_quarter | int | Same channel, previous quarter; null for the first quarter in the data |
| signups_change | decimal | (signups − prior) / prior; null when prior is null or 0 |
| share_of_signups | decimal | Channel's share of all sign-ups that quarter |
| ad_spend | decimal | Simulated spend for the channel and quarter; 0 for channels with no spend |
| cost_per_signup | decimal | ad_spend / signups; null when signups or ad_spend is 0 |
| is_simulated | boolean | Always true |

Tests: unique key; shares sum to 1 per quarter; signups ≥ 0; signups_prior_quarter null only in the first quarter.

## Funnel mart

`fct_visit_funnel_by_channel`. Unique key (channel, cohort_month, milestone). Long format, so Tableau can pivot it and new milestones add rows, not columns.

| Column | Type | Meaning |
|---|---|---|
| channel | text | Canonical acquisition channel |
| cohort_month | date | First day of the customer's signup month |
| milestone | int | 0 = signup, then each visit milestone |
| previous_milestone | int | The step before; null on the signup row |
| customers_reached | int | Customers in the cohort who reached this milestone |
| step_rate | decimal | customers_reached / customers_reached at previous_milestone; null on the signup row |
| avg_days_from_previous | decimal | Average days from previous milestone to this one; null on the signup row |
| ad_spend | decimal | Simulated spend for the channel and month; signup row only, null on other rows |
| is_simulated | boolean | Always true |

Tests at minimum: unique key; not_null on keys; accepted_values on channel; customers_reached non-increasing as milestone rises; step_rate within 0–1.

**Rolling months up to quarters** (dashboard): sum `customers_reached` and `ad_spend`, recompute `step_rate` from the sums, and weight `avg_days_from_previous` by `customers_reached`. Never average stored rates. A quarter filter selects the quarter containing `cohort_month`.

## Cohort mart

`fct_customer_cohorts`. Unique key (channel, cohort_quarter, quarters_since_signup).

| Column | Type | Meaning |
|---|---|---|
| channel | text | Canonical acquisition channel |
| cohort_quarter | date | First day of the signup quarter |
| quarters_since_signup | int | 0 = signup quarter, up to the horizon |
| cohort_size | int | Customers who signed up in the cohort |
| active_customers | int | Cohort customers with ≥ 1 visit in that quarter |
| active_rate | decimal | active_customers / cohort_size |
| visits | int | Visits by cohort customers in that quarter |
| visits_per_active_customer | decimal | visits / active_customers |
| revenue | decimal | Simulated order totals in that quarter |
| average_order | decimal | revenue / visits |
| is_simulated | boolean | Always true |

Tests: unique key; active_customers ≤ cohort_size; rates within 0–1; no rows for quarters after the data ends.

## Recent cohorts

The marts carry every cohort, including ones too young to reach later milestones or quarters; they add no maturity flag. The dashboard filters by default: funnel cohort months at least 6 months before the data ends, cohort quarters at least 4 quarters old.

## Exports

The dashboard reads only the three marts, exported to `data/export/<mart>.csv`.

- UTF-8, comma-delimited, header row, columns in the order listed above.
- Dates `YYYY-MM-DD`; booleans `true` / `false`; null is an empty cell.
- Rounding (rounded, not zero-padded): shares and rates (`signups_change`, `share_of_signups`, `step_rate`, `active_rate`) 6 decimals; money and day averages (`ad_spend`, `cost_per_signup`, `revenue`, `average_order`, `avg_days_from_previous`) 2; `visits_per_active_customer` 4.

## Data catalog (CAP-13)

Every source, model, column, and business term (customer, visit, acquisition channel, milestone, step rate) has a description in dbt YAML; terms use dbt doc blocks so each is defined once. A script generates `CATALOG.md` at the repo root from the dbt manifest. CI fails when a model or column has no description or when `CATALOG.md` is out of date. No hosted docs site.
