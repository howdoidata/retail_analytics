-- One row per customer and visit number: each clean visit numbered in time order per customer (same-time
-- visits by order id), with calendar days since signup and since the previous visit (UTC dates).

with

customers as (

    select * from {{ ref('stg_customers') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

numbered as (

    select
        orders.customer_id,
        row_number() over (
            partition by orders.customer_id
            order by
                orders.created_at,
                orders.id
        ) as visit_number,
        orders.id as order_id,
        cast(orders.created_at as date) as visit_date,
        orders.total as order_total,
        cast(customers.created_at as date) as signup_date,
    from orders
    inner join customers
        on orders.customer_id = customers.id

),

final as (

    select
        customer_id,
        visit_number,
        order_id,
        visit_date,
        order_total,
        date_diff('day', signup_date, visit_date) as days_since_signup,
        date_diff(
            'day',
            lag(visit_date) over (
                partition by customer_id
                order by visit_number
            ),
            visit_date
        ) as days_since_previous_visit,
    from numbered

)

select * from final
