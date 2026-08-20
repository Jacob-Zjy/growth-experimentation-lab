# Pre-analysis plan

## Business question

For customers who purchased during the previous 12 months, should the business send
either promotional creative, and can targeting be improved using heterogeneous
treatment-effect estimates?

## Population and unit

- Eligible population: customers with a purchase in the previous 12 months
- Randomization unit: customer
- Observation window: 14 days after assignment
- Arms: men's email, women's email, no-email control
- Estimand: intent-to-treat effect among eligible customers

## Metrics

| Role | Metric | Definition | Reason |
|---|---|---|---|
| Primary OEC | Revenue per eligible user | total 14-day spend / assigned users | Includes non-purchasers and ties directly to value |
| Diagnostic | Visit rate | visitors / assigned users | Denser leading behavior |
| Diagnostic | Conversion rate | purchasers / assigned users | Purchase behavior, but sparse |
| Integrity | SRM p-value | allocation chi-square test | Detects logging or assignment failures |
| Integrity | Absolute SMD | pre-treatment balance | Detects implementation imbalance |

## Hypotheses

For each planned arm-metric contrast:

- H0: the intent-to-treat effect equals zero.
- H1: the intent-to-treat effect differs from zero.

Tests are two-sided because a campaign may harm outcomes.

## Planned contrasts

1. Men's email versus control
2. Women's email versus control
3. Men's email versus women's email

Each contrast is evaluated for visits, conversion, and revenue per user. The nine
p-values are adjusted with Benjamini-Hochberg. Revenue per user is the decision metric;
the other metrics explain the mechanism.

## Validity gates

1. Fail the readout if SRM p < 0.01 until the assignment/logging issue is understood.
2. Investigate any pre-treatment |SMD| >= 0.10.
3. Confirm unique users, binary outcomes, non-negative revenue, and complete joins.
4. Never replace concurrent controls with a before/after comparison.

## Inference

- Binary outcomes: two-proportion Z test and confidence interval for rate difference
- Revenue per user: Welch test because arm variances need not be equal
- Multiplicity: Benjamini-Hochberg false-discovery-rate control
- Sensitivity: CUPED using prior spend and recency, both measured before treatment

## Power

Use alpha = 0.05 and target power = 0.80. Given the realized sample size and control
baseline, calculate the smallest detectable increase for visits and conversion.
Do not treat a statistically non-significant result as proof of no effect when the
MDE is larger than the smallest business-relevant effect.

## Heterogeneity and uplift

Subgroup tables and meta-learners are exploratory. Models are trained on 60%. Both the model family and target share are selected on the 20% validation split; the fixed model and policy are reported once on the held-out 20% test split. The selected policy must be validated by a future randomized holdout before deployment.

## Decision rule

Recommend launch only when:

1. integrity gates pass;
2. the primary metric's adjusted inference supports positive incremental value;
3. confidence intervals exclude a business-relevant loss;
4. policy economics remain positive under plausible sensitivity scenarios.
