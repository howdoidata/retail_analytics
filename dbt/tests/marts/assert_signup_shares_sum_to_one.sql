-- In every quarter with sign-ups, the channels' shares sum to 1, to within rounding: each share is rounded
-- to 6 decimals, so off by at most 0.0000005, and the total by at most that times the number of channels.

select
    quarter,
    sum(signups) as quarter_signups,
    sum(share_of_signups) as share_total,
from {{ ref('fct_signups_by_channel') }}
group by quarter
having sum(signups) > 0
    and abs(sum(share_of_signups) - 1) > count(*) * 0.0000005
