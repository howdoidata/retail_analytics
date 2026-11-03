{% docs customer %}
A person with a store account: an online account or an in-store email signup. A customer counts once per
email address: emails are compared trimmed and lowercased, and when two accounts share an email the
earliest created one (then the lowest id) is the customer. Test accounts are not customers.
{% enddocs %}

{% docs visit %}
One purchase visit: one online order or one in-store transaction.
{% enddocs %}

{% docs clean_visit %}
A visit that counts: an order whose status, trimmed and lowercased, is `paid` or `complete` (not a
refund), with a total above zero, belonging to a known customer that is not a test account. Every row of
`stg_orders` is a clean visit.
{% enddocs %}

{% docs channel %}
A canonical marketing channel, one of seven: Paid Search, Paid Social, Organic Search, Email, Referral,
In-store, Direct/Unknown. Source labels spelled many ways map to one channel through the `channel_labels`
seed; adding a channel or a label is a seed change.
{% enddocs %}

{% docs test_account %}
A junk customer record left by testing: an email on `@example.com`, or a first or last name `test` (any
case). Test accounts and their orders are dropped in staging.
{% enddocs %}

{% docs utc_timestamp %}
Timestamp in UTC, without a time zone. Source values come in four forms (ISO 8601 with `Z` or with an
offset, `YYYY-MM-DD HH:MM:SS`, `MM/DD/YYYY HH:MM`); values without an offset are UTC.
{% enddocs %}

{% docs acquisition_channel %}
The channel that brought the customer in, by first touch: the channel of the customer's earliest marketing
touch at or before the signup time (`touched_at <= created_at`). Touches at the same time (source
timestamps are whole minutes, so same-minute touches tie) go to the lowest touch id. Touches after signup
never count. A customer with no touch at or before signup has no acquisition channel and fails the build. First
touch is the only attribution rule modeled.
{% enddocs %}

{% docs milestone %}
A visit milestone: the customer's nth visit, for each n in the `milestones` dbt variable (default 1, 2, 3,
5, 10). A customer reaches milestone n on the date of their nth visit. Changing the variable changes no
schema.
{% enddocs %}

{% docs signup %}
A sign-up: a customer's account creation, counted once per customer in the quarter of its UTC signup date
(`dim_customers.signup_date`). A sign-up on 31 March is in the first quarter; one on 1 April, the second.
{% enddocs %}

{% docs ad_spend %}
Simulated marketing spend in dollars, by channel and day, summed over campaigns.
{% enddocs %}

{% docs step_rate %}
The share of customers at the previous step who reach this one: customers reaching this milestone divided by
customers reaching the milestone before it, from 0 to 1. To roll cohorts or months up, sum the customer
counts and divide the sums; never average step rates.
{% enddocs %}

{% docs cohort %}
A signup cohort: the customers acquired by one channel whose signup date falls in one calendar quarter.
Quarters since signup count calendar quarters from the signup quarter (0) to the visit's quarter, so a
sign-up on 31 March and a visit on 1 April are one quarter apart.
{% enddocs %}

{% docs active_customer %}
An active customer in a quarter: a cohort customer with at least one visit in that calendar quarter. To roll
cohorts up, take one quarters_since_signup, sum cohort_size, active_customers, visits, and revenue across
cohorts (channels or cohort quarters), and divide the sums; never sum across offsets (cohort_size repeats on
every offset row and a customer can be active at several) and never average stored rates.
{% enddocs %}
