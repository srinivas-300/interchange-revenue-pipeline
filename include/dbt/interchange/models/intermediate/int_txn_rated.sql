with settled as (

    -- Revenue is only recognised once money actually settles.
    select *
    from {{ ref('int_transaction_lifecycle') }}
    where settled_at is not null

),

card_attributes as (

    -- The interchange rate is keyed by card_program and region, which live on the
    -- card and its company, not on the transaction.
    select
        c.card_id,
        c.company_id,
        c.card_program,
        co.region
    from {{ ref('stg_cards') }} c
    join {{ ref('stg_companies') }} co
        on c.company_id = co.company_id

),

converted as (

    -- The rate and FX joins are left joins on purpose: an inner join would make a
    -- missed match disappear, while a left join turns it into a NULL that the
    -- not_null tests catch and name.
    select
        t.transaction_id,
        ca.company_id,
        t.card_id,
        t.merchant_id,
        t.mcc,
        m.spend_category,
        ca.card_program,
        ca.region,
        t.currency,
        t.settlement_date,
        t.settled_at,
        t.is_disputed,
        t.settled_amount,

        r.bps,
        rw.cashback_pct,
        fx.usd_rate,
        (t.settled_amount * fx.usd_rate)::number(18,6) as settled_amount_usd,

        t._loaded_at_utc

    from settled t

    join card_attributes ca
        on t.card_id = ca.card_id

    -- As-of join: the rate version in effect on the settlement date. valid_from is
    -- inclusive and valid_to exclusive, so a date on the boundary matches exactly
    -- one version. The staging overlap test is what makes that guarantee hold.
    left join {{ ref('stg_interchange_rates') }} r
        on  t.mcc = r.mcc
        and ca.card_program = r.card_program
        and ca.region = r.region
        and t.settlement_date >= r.valid_from
        and (r.valid_to is null or t.settlement_date < r.valid_to)

    -- Cashback is keyed by spend category, so the MCC has to be translated first.
    left join {{ ref('mcc_categories') }} m
        on t.mcc = m.mcc

    left join {{ ref('stg_rewards_rates') }} rw
        on  m.spend_category = rw.spend_category
        and t.settlement_date >= rw.valid_from
        and (rw.valid_to is null or t.settlement_date < rw.valid_to)

    -- USD rows carry usd_rate = 1, so domestic and cross-border share one code path.
    left join {{ ref('stg_fx_rates') }} fx
        on  t.currency = fx.currency
        and t.settlement_date = fx.rate_date

),

components as (

    select
        *,
        (settled_amount_usd * bps / 10000)::number(18,6) as gross_interchange_usd,

        -- Modelled from the vars in dbt_project.yml: a bps share plus a fixed charge
        -- per transaction, which is how card networks actually price.
        (  settled_amount_usd * {{ var('network_fee_bps') }} / 10000
         + {{ var('network_fee_fixed_usd') }}
        )::number(18,6) as network_fee_usd,

        (settled_amount_usd * cashback_pct)::number(18,6) as rewards_accrued_usd

    from converted

)

select
    transaction_id,
    company_id,
    card_id,
    merchant_id,
    mcc,
    spend_category,
    card_program,
    region,
    currency,

    settlement_date,
    settled_at,
    is_disputed,

    settled_amount,
    usd_rate,
    settled_amount_usd,

    bps,
    cashback_pct,

    gross_interchange_usd,
    network_fee_usd,
    rewards_accrued_usd,

    -- Subtracting the stored components rather than recomputing them keeps the four
    -- money columns internally consistent: gross - fee - rewards ties to net exactly.
    (gross_interchange_usd - network_fee_usd - rewards_accrued_usd)::number(18,6)
        as net_interchange_usd,

    _loaded_at_utc
from components
