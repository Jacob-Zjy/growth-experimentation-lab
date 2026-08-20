"""Heterogeneous treatment-effect models and honest policy evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.integrate import trapezoid
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from growth_lab.config import MODEL_DIR, RANDOM_SEED, ensure_directories

NUMERIC_FEATURES = [
    "recency_months",
    "prior_12m_spend",
    "prior_mens_buyer",
    "prior_womens_buyer",
    "is_new_customer",
]
CATEGORICAL_FEATURES = ["history_segment", "geography_type", "prior_channel"]
FEATURES = [*NUMERIC_FEATURES, *CATEGORICAL_FEATURES]


def _outcome_model(seed: int = RANDOM_SEED) -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(
        learning_rate=0.06,
        max_iter=120,
        max_leaf_nodes=15,
        min_samples_leaf=50,
        l2_regularization=1.0,
        random_state=seed,
    )


def _effect_model(seed: int = RANDOM_SEED) -> HistGradientBoostingRegressor:
    return HistGradientBoostingRegressor(
        learning_rate=0.06,
        max_iter=120,
        max_leaf_nodes=15,
        min_samples_leaf=50,
        l2_regularization=1.0,
        random_state=seed,
    )


class SLearner:
    """One outcome model with treatment appended as a feature."""

    def __init__(self, seed: int = RANDOM_SEED):
        self.model = _outcome_model(seed)

    def fit(self, x: np.ndarray, treatment: np.ndarray, outcome: np.ndarray) -> SLearner:
        design = np.column_stack([x, treatment])
        self.model.fit(design, outcome)
        return self

    def predict_uplift(self, x: np.ndarray) -> np.ndarray:
        treated = np.column_stack([x, np.ones(len(x))])
        control = np.column_stack([x, np.zeros(len(x))])
        return self.model.predict_proba(treated)[:, 1] - self.model.predict_proba(control)[:, 1]


class TLearner:
    """Separate outcome models for treated and control observations."""

    def __init__(self, seed: int = RANDOM_SEED):
        self.treated_model = _outcome_model(seed)
        self.control_model = _outcome_model(seed + 1)

    def fit(self, x: np.ndarray, treatment: np.ndarray, outcome: np.ndarray) -> TLearner:
        treated = treatment == 1
        control = ~treated
        self.treated_model.fit(x[treated], outcome[treated])
        self.control_model.fit(x[control], outcome[control])
        return self

    def predict_uplift(self, x: np.ndarray) -> np.ndarray:
        return self.treated_model.predict_proba(x)[:, 1] - self.control_model.predict_proba(x)[:, 1]


class XLearner:
    """X-learner with propensity-weighted imputed treatment effects."""

    def __init__(self, seed: int = RANDOM_SEED):
        self.mu_treated = _outcome_model(seed)
        self.mu_control = _outcome_model(seed + 1)
        self.tau_treated = _effect_model(seed + 2)
        self.tau_control = _effect_model(seed + 3)
        self.propensity_: float | None = None

    def fit(self, x: np.ndarray, treatment: np.ndarray, outcome: np.ndarray) -> XLearner:
        treated = treatment == 1
        control = ~treated
        self.mu_treated.fit(x[treated], outcome[treated])
        self.mu_control.fit(x[control], outcome[control])

        imputed_treated_effect = outcome[treated] - self.mu_control.predict_proba(x[treated])[:, 1]
        imputed_control_effect = self.mu_treated.predict_proba(x[control])[:, 1] - outcome[control]
        self.tau_treated.fit(x[treated], imputed_treated_effect)
        self.tau_control.fit(x[control], imputed_control_effect)
        self.propensity_ = float(treatment.mean())
        return self

    def predict_uplift(self, x: np.ndarray) -> np.ndarray:
        if self.propensity_ is None:
            raise RuntimeError("XLearner must be fitted before prediction.")
        effect_from_treated = self.tau_treated.predict(x)
        effect_from_control = self.tau_control.predict(x)
        return self.propensity_ * effect_from_control + (1 - self.propensity_) * effect_from_treated


def make_encoder() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("numeric", StandardScaler(), NUMERIC_FEATURES),
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )


def qini_curve(
    outcome: np.ndarray,
    treatment: np.ndarray,
    uplift_score: np.ndarray,
) -> pd.DataFrame:
    """Cumulative incremental outcomes versus a random-targeting baseline."""
    order = np.argsort(-np.asarray(uplift_score))
    y = np.asarray(outcome, dtype=float)[order]
    w = np.asarray(treatment, dtype=int)[order]
    cumulative_treated = np.cumsum(w)
    cumulative_control = np.cumsum(1 - w)
    cumulative_y_treated = np.cumsum(y * w)
    cumulative_y_control = np.cumsum(y * (1 - w))
    qini = cumulative_y_treated - cumulative_y_control * (
        cumulative_treated / np.maximum(cumulative_control, 1)
    )
    fraction = np.arange(1, len(y) + 1) / len(y)
    random_baseline = fraction * qini[-1]
    return pd.DataFrame(
        {
            "targeted_fraction": fraction,
            "qini": qini,
            "random_baseline": random_baseline,
        }
    )


def qini_coefficient(curve: pd.DataFrame) -> float:
    """Area between the model and random Qini curves, scaled per observation."""
    x = curve["targeted_fraction"].to_numpy()
    area = trapezoid(
        curve["qini"].to_numpy() - curve["random_baseline"].to_numpy(),
        x=x,
    )
    return float(area / len(curve))


def uplift_curve(
    outcome: np.ndarray,
    treatment: np.ndarray,
    uplift_score: np.ndarray,
) -> pd.DataFrame:
    order = np.argsort(-np.asarray(uplift_score))
    y = np.asarray(outcome, dtype=float)[order]
    w = np.asarray(treatment, dtype=int)[order]
    cumulative_treated = np.cumsum(w)
    cumulative_control = np.cumsum(1 - w)
    treated_rate = np.cumsum(y * w) / np.maximum(cumulative_treated, 1)
    control_rate = np.cumsum(y * (1 - w)) / np.maximum(cumulative_control, 1)
    fraction = np.arange(1, len(y) + 1) / len(y)
    return pd.DataFrame(
        {
            "targeted_fraction": fraction,
            "uplift": treated_rate - control_rate,
        }
    )


def uplift_at_fraction(
    outcome: np.ndarray,
    treatment: np.ndarray,
    uplift_score: np.ndarray,
    fraction: float,
) -> float:
    count = max(2, int(np.ceil(len(outcome) * fraction)))
    selected = np.argsort(-np.asarray(uplift_score))[:count]
    y = np.asarray(outcome)[selected]
    w = np.asarray(treatment)[selected]
    if w.sum() == 0 or (1 - w).sum() == 0:
        return np.nan
    return float(y[w == 1].mean() - y[w == 0].mean())


def evaluate_scores(
    outcome: np.ndarray,
    treatment: np.ndarray,
    scores: np.ndarray,
) -> tuple[dict[str, float], pd.DataFrame]:
    qini = qini_curve(outcome, treatment, scores)
    ucurve = uplift_curve(outcome, treatment, scores)
    return (
        {
            "qini_coefficient": qini_coefficient(qini),
            "auuc": float(trapezoid(ucurve["uplift"], x=ucurve["targeted_fraction"])),
            "uplift_at_10pct": uplift_at_fraction(outcome, treatment, scores, 0.10),
            "uplift_at_30pct": uplift_at_fraction(outcome, treatment, scores, 0.30),
        },
        qini,
    )


def policy_value_curve(
    outcome: np.ndarray,
    treatment: np.ndarray,
    uplift_score: np.ndarray,
    value_per_incremental_outcome: float = 5.0,
    contact_cost: float = 0.50,
    steps: int = 100,
) -> pd.DataFrame:
    """Estimate an offline targeting policy with inverse-propensity weighting.

    `contact_cost` represents both delivery cost and the opportunity cost of using a
    limited customer-contact slot. It is an explicit scenario input, not an observed
    field in the Hillstrom data.
    """
    order = np.argsort(-np.asarray(uplift_score))
    y = np.asarray(outcome, dtype=float)[order]
    w = np.asarray(treatment, dtype=int)[order]
    propensity = w.mean()
    if propensity <= 0 or propensity >= 1:
        raise ValueError("Both treatment and control observations are required.")

    individual_ipw = w * y / propensity - (1 - w) * y / (1 - propensity)
    cumulative_incremental = np.cumsum(individual_ipw)
    fractions = np.linspace(0.01, 1.0, steps)
    rows = []
    for fraction in fractions:
        targeted = max(1, int(np.ceil(len(y) * fraction)))
        incremental = float(cumulative_incremental[targeted - 1])
        value = incremental * value_per_incremental_outcome
        cost = targeted * contact_cost
        rows.append(
            {
                "targeted_fraction": fraction,
                "targeted_users": targeted,
                "estimated_incremental_outcomes": incremental,
                "gross_value": value,
                "contact_cost": cost,
                "estimated_net_value": value - cost,
                "value_per_incremental_outcome": value_per_incremental_outcome,
                "cost_per_contact": contact_cost,
            }
        )
    return pd.DataFrame(rows)


@dataclass
class UpliftRun:
    model_comparison: pd.DataFrame
    qini_curves: pd.DataFrame
    policy_curve: pd.DataFrame
    scored_validation: pd.DataFrame
    scored_test: pd.DataFrame
    best_model: str
    selected_target_fraction: float
    model_path: Path


def _scored_frame(frame: pd.DataFrame, scores: np.ndarray) -> pd.DataFrame:
    scored = frame[["customer_id", "treatment_arm", "treatment", "outcome"]].copy()
    scored["uplift_score"] = scores
    scored["rank_percentile"] = scored["uplift_score"].rank(
        ascending=False, pct=True, method="first"
    )
    return scored


def train_and_evaluate_uplift(
    frame: pd.DataFrame,
    treatment_arm: str = "mens_email",
    outcome_column: str = "visited_14d",
    seed: int = RANDOM_SEED,
    value_per_incremental_outcome: float = 5.0,
    contact_cost: float = 0.50,
) -> UpliftRun:
    """Train on 60%, select model and policy on 20%, then evaluate once on 20%."""
    ensure_directories()
    binary = frame[frame["treatment_arm"].isin(["control", treatment_arm])].copy()
    binary["treatment"] = binary["treatment_arm"].eq(treatment_arm).astype(int)
    binary["outcome"] = binary[outcome_column].astype(int)
    stratification = binary["treatment"].astype(str) + "_" + binary["outcome"].astype(str)

    train, temporary = train_test_split(
        binary,
        test_size=0.40,
        random_state=seed,
        stratify=stratification,
    )
    temporary_strata = temporary["treatment"].astype(str) + "_" + temporary["outcome"].astype(str)
    validation, test = train_test_split(
        temporary,
        test_size=0.50,
        random_state=seed + 1,
        stratify=temporary_strata,
    )

    encoder = make_encoder()
    x_train = encoder.fit_transform(train[FEATURES])
    x_validation = encoder.transform(validation[FEATURES])
    x_test = encoder.transform(test[FEATURES])
    w_train = train["treatment"].to_numpy(dtype=int)
    y_train = train["outcome"].to_numpy(dtype=int)

    models = {
        "s_learner": SLearner(seed),
        "t_learner": TLearner(seed),
        "x_learner": XLearner(seed),
    }
    comparison_rows: list[dict[str, float | str | int]] = []
    test_curves: list[pd.DataFrame] = []
    validation_scores_by_model: dict[str, np.ndarray] = {}
    test_scores_by_model: dict[str, np.ndarray] = {}

    for name, model in models.items():
        model.fit(x_train, w_train, y_train)
        validation_scores = model.predict_uplift(x_validation)
        test_scores = model.predict_uplift(x_test)
        validation_scores_by_model[name] = validation_scores
        test_scores_by_model[name] = test_scores

        validation_metrics, _ = evaluate_scores(
            validation["outcome"].to_numpy(),
            validation["treatment"].to_numpy(),
            validation_scores,
        )
        test_metrics, test_curve = evaluate_scores(
            test["outcome"].to_numpy(),
            test["treatment"].to_numpy(),
            test_scores,
        )
        test_curve["model"] = name
        test_curves.append(test_curve)
        comparison_rows.append(
            {
                "model": name,
                "validation_qini": validation_metrics["qini_coefficient"],
                "test_qini": test_metrics["qini_coefficient"],
                "test_auuc": test_metrics["auuc"],
                "test_uplift_at_10pct": test_metrics["uplift_at_10pct"],
                "test_uplift_at_30pct": test_metrics["uplift_at_30pct"],
                "train_rows": len(train),
                "validation_rows": len(validation),
                "test_rows": len(test),
            }
        )

    model_comparison = pd.DataFrame(comparison_rows).sort_values("validation_qini", ascending=False)
    best_model = str(model_comparison.iloc[0]["model"])
    best_validation_scores = validation_scores_by_model[best_model]
    best_test_scores = test_scores_by_model[best_model]

    validation_policy = policy_value_curve(
        validation["outcome"].to_numpy(),
        validation["treatment"].to_numpy(),
        best_validation_scores,
        value_per_incremental_outcome=value_per_incremental_outcome,
        contact_cost=contact_cost,
    )
    selected_target_fraction = float(
        validation_policy.loc[
            validation_policy["estimated_net_value"].idxmax(), "targeted_fraction"
        ]
    )
    test_policy = policy_value_curve(
        test["outcome"].to_numpy(),
        test["treatment"].to_numpy(),
        best_test_scores,
        value_per_incremental_outcome=value_per_incremental_outcome,
        contact_cost=contact_cost,
    )
    validation_policy["evaluation_split"] = "validation"
    test_policy["evaluation_split"] = "test"
    policy = pd.concat([validation_policy, test_policy], ignore_index=True)
    policy["selected_on_validation"] = np.isclose(
        policy["targeted_fraction"], selected_target_fraction
    )

    scored_validation = _scored_frame(validation, best_validation_scores)
    scored_test = _scored_frame(test, best_test_scores)

    model_path = MODEL_DIR / "uplift_bundle.joblib"
    joblib.dump(
        {
            "encoder": encoder,
            "model": models[best_model],
            "model_name": best_model,
            "features": FEATURES,
            "treatment_arm": treatment_arm,
            "outcome_column": outcome_column,
            "seed": seed,
        },
        model_path,
    )
    return UpliftRun(
        model_comparison=model_comparison,
        qini_curves=pd.concat(test_curves, ignore_index=True),
        policy_curve=policy,
        scored_validation=scored_validation,
        scored_test=scored_test,
        best_model=best_model,
        selected_target_fraction=selected_target_fraction,
        model_path=model_path,
    )
