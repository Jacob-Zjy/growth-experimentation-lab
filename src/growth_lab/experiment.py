"""Experiment diagnostics, frequentist inference, power, and CUPED."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.stats import chisquare, norm, ttest_ind
from scipy.stats import t as student_t
from sklearn.linear_model import LinearRegression
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize, proportions_ztest

from growth_lab.config import ALL_ARMS, CONTROL_ARM, TREATMENT_ARMS


@dataclass(frozen=True)
class ExperimentSpec:
    alpha: float = 0.05
    power: float = 0.80
    control_arm: str = CONTROL_ARM
    primary_metric: str = "revenue_14d"
    diagnostic_metrics: tuple[str, ...] = ("visited_14d", "converted_14d")


BINARY_OUTCOMES = ("visited_14d", "converted_14d")
CONTINUOUS_OUTCOMES = ("revenue_14d",)
OUTCOME_LABELS = {
    "visited_14d": "visit_rate",
    "converted_14d": "conversion_rate",
    "revenue_14d": "revenue_per_user",
}


def sample_ratio_mismatch(
    frame: pd.DataFrame,
    expected_proportions: dict[str, float] | None = None,
) -> dict[str, float | bool]:
    """Chi-square test that the executed split matches the planned allocation."""
    expected_proportions = expected_proportions or {arm: 1 / 3 for arm in ALL_ARMS}
    observed = frame["treatment_arm"].value_counts().reindex(expected_proportions).fillna(0)
    expected = np.array([expected_proportions[arm] * len(frame) for arm in observed.index])
    statistic, p_value = chisquare(observed.to_numpy(), expected)
    return {
        "statistic": float(statistic),
        "p_value": float(p_value),
        "srm_detected": bool(p_value < 0.01),
        "max_allocation_deviation_pp": float(
            100 * np.max(np.abs(observed.to_numpy() / len(frame) - expected / len(frame)))
        ),
    }


def _standardized_mean_difference(treatment: pd.Series, control: pd.Series) -> float:
    variance = (treatment.var(ddof=1) + control.var(ddof=1)) / 2
    if not np.isfinite(variance) or variance <= 0:
        return 0.0
    return float((treatment.mean() - control.mean()) / np.sqrt(variance))


def covariate_balance(frame: pd.DataFrame) -> pd.DataFrame:
    """Compare every treatment arm with control using absolute SMD."""
    numeric = frame[
        [
            "recency_months",
            "prior_12m_spend",
            "prior_mens_buyer",
            "prior_womens_buyer",
            "is_new_customer",
        ]
    ].astype(float)
    categorical = pd.get_dummies(
        frame[["history_segment", "geography_type", "prior_channel"]],
        prefix_sep="=",
        dtype=float,
    )
    covariates = pd.concat([numeric, categorical], axis=1)
    rows: list[dict[str, float | str | bool]] = []
    for arm in TREATMENT_ARMS:
        treatment_mask = frame["treatment_arm"].eq(arm).to_numpy()
        control_mask = frame["treatment_arm"].eq(CONTROL_ARM).to_numpy()
        for column in covariates.columns:
            smd = _standardized_mean_difference(
                covariates.loc[treatment_mask, column],
                covariates.loc[control_mask, column],
            )
            rows.append(
                {
                    "comparison": f"{arm}_vs_{CONTROL_ARM}",
                    "covariate": column,
                    "smd": smd,
                    "absolute_smd": abs(smd),
                    "passes_0_10_rule": abs(smd) < 0.10,
                }
            )
    return pd.DataFrame(rows).sort_values(["comparison", "absolute_smd"], ascending=[True, False])


def _binary_test(treatment: np.ndarray, control: np.ndarray, alpha: float) -> dict[str, float]:
    successes = np.array([treatment.sum(), control.sum()])
    observations = np.array([len(treatment), len(control)])
    statistic, p_value = proportions_ztest(successes, observations, alternative="two-sided")
    treatment_mean = treatment.mean()
    control_mean = control.mean()
    difference = treatment_mean - control_mean
    standard_error = np.sqrt(
        treatment_mean * (1 - treatment_mean) / len(treatment)
        + control_mean * (1 - control_mean) / len(control)
    )
    critical = norm.ppf(1 - alpha / 2)
    return {
        "statistic": float(statistic),
        "p_value": float(p_value),
        "standard_error": float(standard_error),
        "ci_low": float(difference - critical * standard_error),
        "ci_high": float(difference + critical * standard_error),
    }


def _welch_test(treatment: np.ndarray, control: np.ndarray, alpha: float) -> dict[str, float]:
    statistic, p_value = ttest_ind(treatment, control, equal_var=False)
    variance_t = treatment.var(ddof=1) / len(treatment)
    variance_c = control.var(ddof=1) / len(control)
    standard_error = np.sqrt(variance_t + variance_c)
    numerator = (variance_t + variance_c) ** 2
    denominator = variance_t**2 / (len(treatment) - 1) + variance_c**2 / (len(control) - 1)
    degrees_freedom = numerator / denominator if denominator > 0 else np.inf
    critical = student_t.ppf(1 - alpha / 2, degrees_freedom)
    difference = treatment.mean() - control.mean()
    return {
        "statistic": float(statistic),
        "p_value": float(p_value),
        "standard_error": float(standard_error),
        "ci_low": float(difference - critical * standard_error),
        "ci_high": float(difference + critical * standard_error),
    }


def pairwise_tests(frame: pd.DataFrame, spec: ExperimentSpec | None = None) -> pd.DataFrame:
    """Test all three pairwise arm contrasts and adjust the nine p-values together."""
    spec = spec or ExperimentSpec()
    comparisons = (
        ("mens_email", "control"),
        ("womens_email", "control"),
        ("mens_email", "womens_email"),
    )
    rows: list[dict[str, float | str | int]] = []
    for treatment_arm, control_arm in comparisons:
        treatment_rows = frame[frame["treatment_arm"].eq(treatment_arm)]
        control_rows = frame[frame["treatment_arm"].eq(control_arm)]
        for outcome in (*BINARY_OUTCOMES, *CONTINUOUS_OUTCOMES):
            treatment = treatment_rows[outcome].to_numpy(dtype=float)
            control = control_rows[outcome].to_numpy(dtype=float)
            result = (
                _binary_test(treatment, control, spec.alpha)
                if outcome in BINARY_OUTCOMES
                else _welch_test(treatment, control, spec.alpha)
            )
            treatment_mean = treatment.mean()
            control_mean = control.mean()
            absolute_lift = treatment_mean - control_mean
            relative_lift = absolute_lift / control_mean if control_mean != 0 else np.nan
            rows.append(
                {
                    "comparison": f"{treatment_arm}_vs_{control_arm}",
                    "treatment_arm": treatment_arm,
                    "control_arm": control_arm,
                    "outcome": OUTCOME_LABELS[outcome],
                    "outcome_column": outcome,
                    "test": "two_proportion_z" if outcome in BINARY_OUTCOMES else "welch_t",
                    "n_treatment": len(treatment),
                    "n_control": len(control),
                    "mean_treatment": treatment_mean,
                    "mean_control": control_mean,
                    "absolute_lift": absolute_lift,
                    "relative_lift": relative_lift,
                    **result,
                }
            )
    results = pd.DataFrame(rows)
    rejected, adjusted, _, _ = multipletests(
        results["p_value"].to_numpy(), alpha=spec.alpha, method="fdr_bh"
    )
    results["p_value_bh"] = adjusted
    results["reject_h0_bh"] = rejected
    return results


def _mde_upper_rate(baseline: float, n_per_arm: int, alpha: float, power: float) -> float:
    solver = NormalIndPower()
    effect = solver.solve_power(
        effect_size=None,
        nobs1=n_per_arm,
        alpha=alpha,
        power=power,
        ratio=1,
        alternative="two-sided",
    )
    upper = min(0.999999, baseline + 0.50)
    return float(
        brentq(
            lambda candidate: abs(proportion_effectsize(candidate, baseline)) - effect,
            baseline + 1e-9,
            upper,
        )
    )


def power_analysis(frame: pd.DataFrame, spec: ExperimentSpec | None = None) -> pd.DataFrame:
    """Observed-design MDE for each binary metric and treatment-control comparison."""
    spec = spec or ExperimentSpec()
    rows: list[dict[str, float | str | int]] = []
    control = frame[frame["treatment_arm"].eq(spec.control_arm)]
    for arm in TREATMENT_ARMS:
        treatment_n = int(frame["treatment_arm"].eq(arm).sum())
        n_per_arm = min(treatment_n, len(control))
        for outcome in BINARY_OUTCOMES:
            baseline = float(control[outcome].mean())
            detectable_rate = _mde_upper_rate(baseline, n_per_arm, spec.alpha, spec.power)
            rows.append(
                {
                    "comparison": f"{arm}_vs_{spec.control_arm}",
                    "outcome": OUTCOME_LABELS[outcome],
                    "baseline_rate": baseline,
                    "n_per_arm": n_per_arm,
                    "alpha": spec.alpha,
                    "target_power": spec.power,
                    "detectable_rate": detectable_rate,
                    "mde_absolute": detectable_rate - baseline,
                    "mde_relative": detectable_rate / baseline - 1,
                }
            )
    return pd.DataFrame(rows)


def _cuped_adjust(outcome: np.ndarray, covariates: np.ndarray) -> tuple[np.ndarray, float]:
    model = LinearRegression().fit(covariates, outcome)
    prediction = model.predict(covariates)
    adjusted = outcome - (prediction - prediction.mean())
    reduction = 1 - adjusted.var(ddof=1) / outcome.var(ddof=1)
    return adjusted, float(reduction)


def cuped_results(frame: pd.DataFrame, spec: ExperimentSpec | None = None) -> pd.DataFrame:
    """Apply single- and multi-covariate CUPED to revenue per user."""
    spec = spec or ExperimentSpec()
    outcome = frame[spec.primary_metric].to_numpy(dtype=float)
    designs = {
        "single_prior_spend": frame[["prior_12m_spend"]].to_numpy(dtype=float),
        "multi_spend_recency": frame[["prior_12m_spend", "recency_months"]].to_numpy(dtype=float),
    }
    rows: list[dict[str, float | str | int | bool]] = []
    for method, covariates in designs.items():
        adjusted, variance_reduction = _cuped_adjust(outcome, covariates)
        working = frame[["treatment_arm"]].copy()
        working["adjusted_revenue"] = adjusted
        for arm in TREATMENT_ARMS:
            treatment = working.loc[working["treatment_arm"].eq(arm), "adjusted_revenue"].to_numpy()
            control = working.loc[
                working["treatment_arm"].eq(spec.control_arm), "adjusted_revenue"
            ].to_numpy()
            result = _welch_test(treatment, control, spec.alpha)
            rows.append(
                {
                    "method": method,
                    "comparison": f"{arm}_vs_{spec.control_arm}",
                    "n_treatment": len(treatment),
                    "n_control": len(control),
                    "adjusted_lift": treatment.mean() - control.mean(),
                    "variance_reduction": variance_reduction,
                    **result,
                }
            )
    results = pd.DataFrame(rows)
    results["reject_h0"] = results["p_value"] < spec.alpha
    return results


def heterogeneity_table(
    frame: pd.DataFrame,
    treatment_arm: str = "mens_email",
    outcome: str = "visited_14d",
    alpha: float = 0.05,
) -> pd.DataFrame:
    """Exploratory subgroup effects with multiplicity correction."""
    working = frame[frame["treatment_arm"].isin([CONTROL_ARM, treatment_arm])].copy()
    working["recency_band"] = pd.cut(
        working["recency_months"],
        bins=[0, 3, 6, 9, np.inf],
        labels=["1-3m", "4-6m", "7-9m", "10-12m"],
    )
    features = ["recency_band", "prior_channel", "geography_type", "is_new_customer"]
    rows: list[dict[str, float | str | int]] = []
    for feature in features:
        for level, subset in working.groupby(feature, observed=True):
            treatment = subset.loc[subset["treatment_arm"].eq(treatment_arm), outcome].to_numpy(
                dtype=float
            )
            control = subset.loc[subset["treatment_arm"].eq(CONTROL_ARM), outcome].to_numpy(
                dtype=float
            )
            if min(len(treatment), len(control)) < 100:
                continue
            result = (
                _binary_test(treatment, control, alpha)
                if outcome in BINARY_OUTCOMES
                else _welch_test(treatment, control, alpha)
            )
            rows.append(
                {
                    "feature": feature,
                    "level": str(level),
                    "outcome": OUTCOME_LABELS[outcome],
                    "n_treatment": len(treatment),
                    "n_control": len(control),
                    "mean_treatment": treatment.mean(),
                    "mean_control": control.mean(),
                    "absolute_lift": treatment.mean() - control.mean(),
                    **result,
                }
            )
    results = pd.DataFrame(rows)
    if results.empty:
        return results
    rejected, adjusted, _, _ = multipletests(
        results["p_value"].to_numpy(), alpha=alpha, method="fdr_bh"
    )
    results["p_value_bh"] = adjusted
    results["reject_h0_bh"] = rejected
    return results
