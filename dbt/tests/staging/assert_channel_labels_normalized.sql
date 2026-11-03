-- M1: labels are looked up trimmed and lowercased, so a seed label in any other form would never match.

select
    label,
from {{ ref('channel_labels') }}
where label != lower(trim(label))
