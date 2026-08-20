import numpy as np

from growth_lab.data import generate_synthetic_experiment
from growth_lab.uplift import (
    policy_value_curve,
    qini_coefficient,
    qini_curve,
    train_and_evaluate_uplift,
)


def test_qini_rewards_correct_ranking():
    rng = np.random.default_rng(9)
    n = 8_000
    feature = rng.normal(size=n)
    treatment = rng.binomial(1, 0.5, n)
    baseline = 0.08
    true_effect = 0.10 * (feature > 0.8)
    outcome = rng.binomial(1, np.clip(baseline + treatment * true_effect, 0, 1))

    good_curve = qini_curve(outcome, treatment, true_effect)
    bad_curve = qini_curve(outcome, treatment, -true_effect)
    assert qini_coefficient(good_curve) > qini_coefficient(bad_curve)


def test_policy_curve_has_expected_columns_and_bounds():
    outcome = np.array([1, 0, 1, 0, 1, 0, 0, 1])
    treatment = np.array([1, 0, 1, 0, 0, 1, 0, 1])
    scores = np.linspace(1, 0, len(outcome))
    policy = policy_value_curve(outcome, treatment, scores, steps=10)

    assert len(policy) == 10
    assert policy["targeted_fraction"].between(0, 1).all()
    assert "estimated_net_value" in policy


def test_target_share_is_selected_on_validation_split():
    frame = generate_synthetic_experiment(n=6_000, seed=24).rename(
        columns={
            "recency": "recency_months",
            "history": "prior_12m_spend",
            "mens": "prior_mens_buyer",
            "womens": "prior_womens_buyer",
            "zip_code": "geography_type",
            "newbie": "is_new_customer",
            "channel": "prior_channel",
            "visit": "visited_14d",
            "conversion": "converted_14d",
            "spend": "revenue_14d",
        }
    )
    run = train_and_evaluate_uplift(frame, seed=24)
    selected = run.policy_curve[run.policy_curve["selected_on_validation"]]
    validation = run.policy_curve[run.policy_curve["evaluation_split"].eq("validation")]
    validation_best = validation.loc[validation["estimated_net_value"].idxmax()]

    assert set(run.policy_curve["evaluation_split"]) == {"validation", "test"}
    assert len(selected) == 2
    assert np.isclose(
        run.selected_target_fraction,
        validation_best["targeted_fraction"],
    )
