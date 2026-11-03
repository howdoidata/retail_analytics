-- M3: every source timestamp and date is in one of its known forms. Checked on the sources, so a value
-- in an unknown form fails even on rows staging later drops.

with

customers as (

    select * from {{ source('raw', 'customers') }}

),

orders as (

    select * from {{ source('raw', 'orders') }}

),

marketing_touches as (

    select * from {{ source('raw', 'marketing_touches') }}

),

ad_spend as (

    select * from {{ source('raw', 'ad_spend') }}

),

unparsed as (

    select
        'customers.created_at' as field,
        created_at as value,
    from customers
    where {{ parse_utc_timestamp('created_at') }} is null

    union all

    select
        'orders.created_at' as field,
        created_at as value,
    from orders
    where {{ parse_utc_timestamp('created_at') }} is null

    union all

    select
        'marketing_touches.touched_at' as field,
        touched_at as value,
    from marketing_touches
    where {{ parse_utc_timestamp('touched_at') }} is null

    union all

    select
        'ad_spend.date' as field,
        date as value,
    from ad_spend
    where {{ parse_date('date') }} is null

)

select * from unparsed
