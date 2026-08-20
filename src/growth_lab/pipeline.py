"""One-command reproducible analysis pipeline."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from growth_lab.config import ARTIFACT_DIR, METRIC_DIR, ensure_directories
from growth_lab.data import prepare_data
from growth_lab.experiment import (
    covariate_balance,
    cuped_results,
    heterogeneity_table,
    pairwise_tests,
    power_analysis,
    sample_ratio_mismatch,
)
from growth_lab.reporting import (
    generate_decision_memo,
    plot_arm_metrics,
    plot_balance,
    plot_policy,
    plot_power,
    plot_qini,
)
from growth_lab.sql import arm_metrics, build_database, data_quality_summary, experiment_frame
from growth_lab.uplift import train_and_evaluate_uplift


def _write_csv(frame: pd.DataFrame, name: str) -> Path:
    path = METRIC_DIR / name
    frame.to_csv(path, index=False)
    return path


def run_pipeline(
    *,
    use_synthetic: bool = False,
    force_download: bool = False,
    value_per_incremental_visit: float = 5.0,
    contact_cost: float = 0.50,
) -> dict[str, str | int | float | bool]:
    if value_per_incremental_visit <= 0:
        raise ValueError("value_per_incremental_visit must be positive.")
    if contact_cost < 0:
        raise ValueError("contact_cost must be non-negative.")

    ensure_directories()
    clean = prepare_data(force_download=force_download, use_synthetic=use_synthetic)
    database = build_database(clean)
    analysis = experiment_frame(database)

    arms = arm_metrics(database)
    quality = data_quality_summary(database)
    srm = sample_ratio_mismatch(analysis)
    balance = covariate_balance(analysis)
    tests = pairwise_tests(analysis)
    power = power_analysis(analysis)
    cuped = cuped_results(analysis)
    heterogeneity = heterogeneity_table(analysis)
    uplift = train_and_evaluate_uplift(
        analysis,
        value_per_incremental_outcome=value_per_incremental_visit,
        contact_cost=contact_cost,
    )

    _write_csv(arms, "arm_metrics.csv")
    _write_csv(quality, "data_quality.csv")
    _write_csv(pd.DataFrame([srm]), "srm_test.csv")
    _write_csv(balance, "covariate_balance.csv")
    _write_csv(tests, "pairwise_tests.csv")
    _write_csv(power, "power_analysis.csv")
    _write_csv(cuped, "cuped_results.csv")
    _write_csv(heterogeneity, "heterogeneity.csv")
    _write_csv(uplift.model_comparison, "uplift_model_comparison.csv")
    _write_csv(uplift.qini_curves, "qini_curves.csv")
    _write_csv(uplift.policy_curve, "policy_curve.csv")
    _write_csv(uplift.scored_validation, "scored_validation_sample.csv")
    _write_csv(uplift.scored_test, "scored_test_sample.csv")

    plot_arm_metrics(arms)
    plot_balance(balance)
    plot_power(power)
    plot_qini(uplift.qini_curves)
    plot_policy(uplift.policy_curve)

    memo = generate_decision_memo(
        output=ARTIFACT_DIR / "experiment_decision_memo.md",
        arm_metrics=arms,
        srm=srm,
        balance=balance,
        tests=tests,
        power=power,
        cuped=cuped,
        model_comparison=uplift.model_comparison,
        policy=uplift.policy_curve,
        best_model=uplift.best_model,
        synthetic=use_synthetic,
    )

    manifest: dict[str, str | int | float | bool] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "synthetic": use_synthetic,
        "rows": len(analysis),
        "database": str(database.relative_to(database.parents[1])),
        "srm_p_value": float(srm["p_value"]),
        "srm_detected": bool(srm["srm_detected"]),
        "best_uplift_model": uplift.best_model,
        "optimal_target_fraction": uplift.selected_target_fraction,
        "value_per_incremental_visit": value_per_incremental_visit,
        "contact_cost": contact_cost,
        "decision_memo": str(memo.relative_to(memo.parents[1])),
    }
    (ARTIFACT_DIR / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Use deterministic synthetic data for a smoke test; not for substantive result claims.",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Redownload and checksum the public dataset.",
    )
    parser.add_argument(
        "--value-per-incremental-visit",
        type=float,
        default=5.0,
        help="Scenario value assigned to one incremental visit (default: 5.0).",
    )
    parser.add_argument(
        "--contact-cost",
        type=float,
        default=0.50,
        help="Scenario delivery plus opportunity cost per contacted user (default: 0.50).",
    )
    arguments = parser.parse_args()
    manifest = run_pipeline(
        use_synthetic=arguments.synthetic,
        force_download=arguments.force_download,
        value_per_incremental_visit=arguments.value_per_incremental_visit,
        contact_cost=arguments.contact_cost,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
