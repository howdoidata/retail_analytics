-- One row per customer: typed, emails normalized (M2), timestamps in UTC (M3),
-- test accounts dropped (M6), and one row per email (M2: earliest created_at, then lowest id).

with

source as (

    select * from {{ source('raw', 'customers') }}

),

typed as (

    select
        cast(id as bigint) as id,
        {{ parse_utc_timestamp('created_at') }} as created_at,
        {{ normalize_email('email') }} as email,
        nullif(first_name, '') as first_name,
        nullif(last_name, '') as last_name,
        nullif(state, '') as state,
        nullif(signup_location, '') as signup_location,
        cast(nullif(accepts_marketing, '') as boolean) as accepts_marketing,
    from source

),

real_customers as (

    select * from typed
    where coalesce(email, '') not like '%@example.com'
        and coalesce(lower(trim(first_name)), '') != 'test'
        and coalesce(lower(trim(last_name)), '') != 'test'

),

deduplicated as (

    select * from real_customers
    qualify row_number() over (
        partition by email
        order by
            created_at,
            id
    ) = 1

),

final as (

    select * from deduplicated

)

select * from final
