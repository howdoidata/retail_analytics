-- The grid is complete: rows = channels in the seed x quarters from the first to the last, contiguous.

with

signups as (

    select * from {{ ref('fct_signups_by_channel') }}

),

channels as (

    select count(*) as channels from {{ ref('channels') }}

),

span as (

    select
        count(*) as grid_rows,
        count(distinct quarter) as quarters,
        coalesce(date_diff('quarter', min(quarter), max(quarter)) + 1, 0) as quarters_in_span,
    from signups

)

select
    span.grid_rows,
    span.quarters,
    span.quarters_in_span,
    channels.channels,
from span
cross join channels
where span.quarters != span.quarters_in_span
    or span.grid_rows != channels.channels * span.quarters_in_span
