-- Rebuild the analytical mart from the normalized source_frame registered by Python.
-- Grain and ownership are explicit so metric definitions remain auditable.

CREATE OR REPLACE TABLE customer_profile AS
SELECT
    CAST(customer_id AS BIGINT) AS customer_id,
    CAST(recency AS INTEGER) AS recency_months,
    CAST(history_segment AS VARCHAR) AS history_segment,
    CAST(history AS DOUBLE) AS prior_12m_spend,
    CAST(mens AS BOOLEAN) AS prior_mens_buyer,
    CAST(womens AS BOOLEAN) AS prior_womens_buyer,
    CAST(zip_code AS VARCHAR) AS geography_type,
    CAST(newbie AS BOOLEAN) AS is_new_customer,
    CAST(channel AS VARCHAR) AS prior_channel
FROM source_frame;

CREATE OR REPLACE TABLE experiment_assignment AS
SELECT
    CAST(customer_id AS BIGINT) AS customer_id,
    CAST(treatment_arm AS VARCHAR) AS treatment_arm,
    CAST(is_treated AS BOOLEAN) AS is_treated
FROM source_frame;

CREATE OR REPLACE TABLE experiment_outcome AS
SELECT
    CAST(customer_id AS BIGINT) AS customer_id,
    CAST(visit AS INTEGER) AS visited_14d,
    CAST(conversion AS INTEGER) AS converted_14d,
    CAST(spend AS DOUBLE) AS revenue_14d
FROM source_frame;

CREATE OR REPLACE VIEW experiment_analysis AS
SELECT
    p.customer_id,
    p.recency_months,
    p.history_segment,
    p.prior_12m_spend,
    p.prior_mens_buyer,
    p.prior_womens_buyer,
    p.geography_type,
    p.is_new_customer,
    p.prior_channel,
    a.treatment_arm,
    a.is_treated,
    o.visited_14d,
    o.converted_14d,
    o.revenue_14d
FROM customer_profile p
JOIN experiment_assignment a USING (customer_id)
JOIN experiment_outcome o USING (customer_id);

CREATE OR REPLACE VIEW arm_metrics AS
SELECT
    treatment_arm,
    COUNT(*) AS users,
    AVG(visited_14d) AS visit_rate,
    AVG(converted_14d) AS conversion_rate,
    AVG(revenue_14d) AS revenue_per_user,
    SUM(revenue_14d) AS total_revenue
FROM experiment_analysis
GROUP BY treatment_arm;

CREATE OR REPLACE VIEW segment_metrics AS
SELECT
    treatment_arm,
    prior_channel,
    geography_type,
    CASE
        WHEN recency_months <= 3 THEN '01_recent_1_3m'
        WHEN recency_months <= 6 THEN '02_active_4_6m'
        WHEN recency_months <= 9 THEN '03_cooling_7_9m'
        ELSE '04_lapsed_10_12m'
    END AS recency_band,
    COUNT(*) AS users,
    AVG(visited_14d) AS visit_rate,
    AVG(converted_14d) AS conversion_rate,
    AVG(revenue_14d) AS revenue_per_user
FROM experiment_analysis
GROUP BY ALL;

CREATE OR REPLACE VIEW data_quality_summary AS
SELECT 'row_count' AS check_name, COUNT(*)::DOUBLE AS observed_value, 64000::DOUBLE AS expected_value
FROM experiment_analysis
UNION ALL
SELECT 'unique_customer_count', COUNT(DISTINCT customer_id)::DOUBLE, COUNT(*)::DOUBLE
FROM experiment_analysis
UNION ALL
SELECT 'invalid_visit_values', COUNT(*)::DOUBLE, 0::DOUBLE
FROM experiment_analysis WHERE visited_14d NOT IN (0, 1)
UNION ALL
SELECT 'invalid_conversion_values', COUNT(*)::DOUBLE, 0::DOUBLE
FROM experiment_analysis WHERE converted_14d NOT IN (0, 1)
UNION ALL
SELECT 'negative_revenue_rows', COUNT(*)::DOUBLE, 0::DOUBLE
FROM experiment_analysis WHERE revenue_14d < 0;
