from pathlib import Path

from growth_lab.data import generate_synthetic_experiment
from growth_lab.sql import arm_metrics, build_database, experiment_frame


def test_duckdb_mart_round_trip(tmp_path: Path):
    source = generate_synthetic_experiment(n=1_500, seed=3)
    database = tmp_path / "test.duckdb"
    build_database(source, database)
    analysis = experiment_frame(database)
    metrics = arm_metrics(database)

    assert len(analysis) == 1_500
    assert analysis["customer_id"].is_unique
    assert set(metrics["treatment_arm"]) == {"control", "mens_email", "womens_email"}
    assert int(metrics["users"].sum()) == 1_500
