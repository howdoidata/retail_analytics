-- One row per product, typed.

with

source as (

    select * from {{ source('raw', 'products') }}

),

final as (

    select
        cast(id as bigint) as id,
        nullif(title, '') as title,
        nullif(category, '') as category,
        cast(list_price as decimal(12, 2)) as list_price,
    from source

)

select * from final
