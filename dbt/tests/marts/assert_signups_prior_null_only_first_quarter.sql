-- signups_prior_quarter is null in the first quarter of the mart and only there.

with

signups as (

    select * from {{ ref('fct_signups_by_channel') }}

),

first_quarter as (

    select min(quarter) as quarter from signups

)

select
    signups.channel,
    signups.quarter,
    signups.signups_prior_quarter,
from signups
cross join first_quarter
where (signups.quarter = first_quarter.quarter) != (signups.signups_prior_quarter is null)
