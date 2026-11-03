-- One row per clean visit: typed, timestamps in UTC (M3), status normalized with refunds dropped (M5),
-- zero-total orders dropped (M6), and only orders of a customer kept in stg_customers (M4 orphans,
-- and orders of the M6 test accounts dropped there).

with

source as (

    select * from {{ source('raw', 'orders') }}

),

customers as (

    select * from {{ ref('stg_customers') }}

),

typed as (

    select
        cast(id as bigint) as id,
        cast(customer_id as bigint) as customer_id,
        {{ parse_utc_timestamp('created_at') }} as created_at,
        nullif(sales_channel, '') as sales_channel,
        case
            when lower(trim(status)) = 'complete' then 'paid'
            else nullif(lower(trim(status)), '')
        end as status,
        cast(subtotal as decimal(12, 2)) as subtotal,
        cast(discount as decimal(12, 2)) as discount,
        cast(total as decimal(12, 2)) as total,
        nullif(currency, '') as currency,
    from source

),

not_refunded as (

    select * from typed
    where status is distinct from 'refunded'
        and status is distinct from 'refund'

),

not_zero_total as (

    select * from not_refunded
    where total is distinct from 0

),

known_customer as (

    select * from not_zero_total
    where customer_id in (select customers.id from customers)

),

final as (

    select * from known_customer

)

select * from final
