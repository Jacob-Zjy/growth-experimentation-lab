# Data dictionary

## Source and grain

One row represents one randomized customer. Raw fields are split into three tables so
pre-treatment features, assignment, and post-treatment outcomes are not mixed.

## `customer_profile`

| Field | Type | Grain/meaning |
|---|---|---|
| `customer_id` | BIGINT | Stable project identifier generated from source row order |
| `recency_months` | INTEGER | Months since the last purchase before the experiment |
| `history_segment` | VARCHAR | Binned prior 12-month spend |
| `prior_12m_spend` | DOUBLE | Spend before treatment; eligible for CUPED |
| `prior_mens_buyer` | BOOLEAN | Bought men's merchandise before treatment |
| `prior_womens_buyer` | BOOLEAN | Bought women's merchandise before treatment |
| `geography_type` | VARCHAR | Urban, suburban, or rural category |
| `is_new_customer` | BOOLEAN | New customer during the prior 12 months |
| `prior_channel` | VARCHAR | Historical purchase channel |

## `experiment_assignment`

| Field | Type | Meaning |
|---|---|---|
| `customer_id` | BIGINT | Join key |
| `treatment_arm` | VARCHAR | `control`, `mens_email`, or `womens_email` |
| `is_treated` | BOOLEAN | Any email versus no email; not used for the three-arm readout |

## `experiment_outcome`

| Field | Type | Meaning |
|---|---|---|
| `customer_id` | BIGINT | Join key |
| `visited_14d` | INTEGER | Site visit during the two-week outcome window |
| `converted_14d` | INTEGER | Purchase during the two-week outcome window |
| `revenue_14d` | DOUBLE | Customer spend during the two-week outcome window |

## Important denominator rule

All rates and revenue per user divide by **assigned eligible users**, not visitors or
purchasers. Changing the denominator would condition on post-treatment behavior and
invalidate the intent-to-treat interpretation.
