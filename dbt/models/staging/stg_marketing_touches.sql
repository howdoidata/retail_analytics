-- One row per marketing touch of a known customer: typed, emails normalized (M2), timestamps in UTC (M3),
-- channel and utm_source labels mapped to canonical channels (M1), and touches whose email matches
-- no customer in stg_customers dropped (M4).

with

source as (

    select * from {{ source('raw', 'marketing_touches') }}

),

channel_labels as (

    select * from {{ ref('channel_labels') }}

),

customers as (

    select * from {{ ref('stg_customers') }}

),

typed as (

    select
        cast(id as bigint) as id,
        {{ normalize_email('customer_email') }} as customer_email,
        {{ parse_utc_timestamp('touched_at') }} as touched_at,
        nullif(lower(trim(channel)), '') as channel_label,
        nullif(campaign, '') as campaign,
        nullif(lower(trim(utm_source)), '') as utm_source,
        nullif(utm_medium, '') as utm_medium,
        nullif(utm_campaign, '') as utm_campaign,
    from source

),

mapped as (

    select
        typed.id,
        typed.customer_email,
        typed.touched_at,
        channel_map.channel,
        typed.campaign,
        typed.utm_source,
        source_map.channel as utm_source_channel,
        typed.utm_medium,
        typed.utm_campaign,
    from typed
    left join channel_labels as channel_map
        on typed.channel_label = channel_map.label
    left join channel_labels as source_map
        on typed.utm_source = source_map.label

),

known_customer as (

    select * from mapped
    where customer_email in (select customers.email from customers)

),

final as (

    select * from known_customer

)

select * from final
