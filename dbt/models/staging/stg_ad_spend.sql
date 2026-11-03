-- One row per date x channel x campaign: typed, dates parsed (M3), channel labels mapped to canonical
-- channels (M1). Simulated spend.

with

source as (

    select * from {{ source('raw', 'ad_spend') }}

),

channel_labels as (

    select * from {{ ref('channel_labels') }}

),

typed as (

    select
        {{ parse_date('date') }} as date,
        nullif(lower(trim(channel)), '') as channel_label,
        nullif(campaign, '') as campaign,
        cast(spend as decimal(12, 2)) as spend,
    from source

),

mapped as (

    select
        typed.date,
        channel_map.channel,
        typed.campaign,
        typed.spend,
    from typed
    left join channel_labels as channel_map
        on typed.channel_label = channel_map.label

),

final as (

    select * from mapped

)

select * from final
