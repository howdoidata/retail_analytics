-- One row per line of a clean visit: typed, and only lines of orders kept in stg_orders.

with

source as (

    select * from {{ source('raw', 'order_lines') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

typed as (

    select
        cast(id as bigint) as id,
        cast(order_id as bigint) as order_id,
        cast(product_id as bigint) as product_id,
        cast(quantity as integer) as quantity,
        cast(unit_price as decimal(12, 2)) as unit_price,
    from source

),

kept_order as (

    select * from typed
    where order_id in (select orders.id from orders)

),

final as (

    select * from kept_order

)

select * from final
