-- Every MCC that appears on a transaction must map to a spend category, otherwise
-- the cashback lookup in int_txn_rated would silently find no rate.
select distinct t.mcc
from {{ ref('int_transaction_lifecycle') }} t
left join {{ ref('mcc_categories') }} m
    on t.mcc = m.mcc
where m.mcc is null
