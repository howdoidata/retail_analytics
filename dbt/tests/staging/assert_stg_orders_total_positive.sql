-- M6: every clean visit has a total above zero.

select
    id,
    total,
from {{ ref('stg_orders') }}
where not total > 0
