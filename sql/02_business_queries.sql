-- Interview-ready examples. These queries are not hard-coded into notebooks.

-- 1. KPI table and absolute lift versus control.
WITH metrics AS (
    SELECT * FROM arm_metrics
), control AS (
    SELECT * FROM metrics WHERE treatment_arm = 'control'
)
SELECT
    m.treatment_arm,
    m.users,
    m.visit_rate,
    m.visit_rate - c.visit_rate AS visit_absolute_lift,
    m.conversion_rate,
    m.conversion_rate - c.conversion_rate AS conversion_absolute_lift,
    m.revenue_per_user,
    m.revenue_per_user - c.revenue_per_user AS revenue_per_user_lift
FROM metrics m
CROSS JOIN control c
ORDER BY m.treatment_arm;

-- 2. Recency segments with at least 500 users per arm.
SELECT
    treatment_arm,
    recency_band,
    SUM(users) AS users,
    SUM(users * visit_rate) / SUM(users) AS visit_rate,
    SUM(users * conversion_rate) / SUM(users) AS conversion_rate,
    SUM(users * revenue_per_user) / SUM(users) AS revenue_per_user
FROM segment_metrics
GROUP BY treatment_arm, recency_band
HAVING SUM(users) >= 500
ORDER BY recency_band, treatment_arm;

-- 3. Funnel consistency check: a conversion without a visit is suspicious.
SELECT
    treatment_arm,
    COUNT(*) FILTER (WHERE converted_14d = 1 AND visited_14d = 0) AS conversion_without_visit,
    COUNT(*) AS users
FROM experiment_analysis
GROUP BY treatment_arm;
