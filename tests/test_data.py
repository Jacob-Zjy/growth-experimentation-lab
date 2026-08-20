from growth_lab.data import generate_synthetic_experiment, validate_hillstrom


def test_synthetic_data_has_valid_three_arm_schema():
    frame = generate_synthetic_experiment(n=3_000, seed=7)
    validate_hillstrom(frame, require_real_size=False)
    assert len(frame) == 3_000
    assert set(frame["treatment_arm"]) == {"control", "mens_email", "womens_email"}
    assert frame["customer_id"].is_unique


def test_synthetic_treatment_increases_visits_on_average():
    frame = generate_synthetic_experiment(n=20_000, seed=8)
    rates = frame.groupby("treatment_arm")["visit"].mean()
    assert rates["mens_email"] > rates["control"]
    assert rates["womens_email"] > rates["control"]
