import numpy as np

from growth_lab.data import generate_synthetic_experiment
from growth_lab.experiment import (
    covariate_balance,
    cuped_results,
    pairwise_tests,
    sample_ratio_mismatch,
)


def _analysis_schema(frame):
    return frame.rename(
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


def test_experiment_diagnostics_and_inference():
    frame = _analysis_schema(generate_synthetic_experiment(n=30_000, seed=42))
    srm = sample_ratio_mismatch(frame)
    balance = covariate_balance(frame)
    tests = pairwise_tests(frame)

    assert not srm["srm_detected"]
    assert balance["absolute_smd"].max() < 0.10
    assert len(tests) == 9
    assert tests["p_value_bh"].between(0, 1).all()
    mens_visit = tests[
        (tests["comparison"] == "mens_email_vs_control") & (tests["outcome"] == "visit_rate")
    ].iloc[0]
    assert mens_visit["absolute_lift"] > 0


def test_cuped_preserves_effect_scale():
    frame = _analysis_schema(generate_synthetic_experiment(n=20_000, seed=12))
    results = cuped_results(frame)
    assert np.isfinite(results["adjusted_lift"]).all()
    assert np.isfinite(results["variance_reduction"]).all()
