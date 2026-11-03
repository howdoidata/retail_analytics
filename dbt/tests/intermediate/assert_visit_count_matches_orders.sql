-- Every clean visit in stg_orders is exactly one row of int_customer_visits.

with

orders as (

    select count(*) as visits from {{ ref('stg_orders') }}

),

customer_visits as (

    select count(*) as visits from {{ ref('int_customer_visits') }}

)

select
    orders.visits as order_rows,
    customer_visits.visits as customer_visit_rows,
from orders
cross join customer_visits
where orders.visits != customer_visits.visits
