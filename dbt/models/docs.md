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
