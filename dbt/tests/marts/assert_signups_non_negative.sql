-- Sign-up counts are never negative.

select
    channel,
    quarter,
    signups,
from {{ ref('fct_signups_by_channel') }}
where signups < 0
