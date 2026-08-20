"""Publication-ready figures and an automatically generated decision memo."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from growth_lab.config import FIGURE_DIR

COLORS = {
    "control": "#9AA0A6",
    "mens_email": "#2563EB",
    "womens_email": "#DB2777",
    "s_learner": "#0F766E",
    "t_learner": "#D97706",
    "x_learner": "#7C3AED",
}


def set_plot_style() -> None:
    sns.set_theme(style="whitegrid", context="talk")
    plt.rcParams.update(
        {
            "figure.dpi": 120,
            "savefig.dpi": 180,
            "axes.titleweight": "bold",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "font.family": "DejaVu Sans",
        }
    )


def plot_arm_metrics(
    arm_metrics: pd.DataFrame, output: Path = FIGURE_DIR / "arm_metrics.png"
) -> Path:
    set_plot_style()
    ordered = (
        arm_metrics.set_index("treatment_arm")
        .reindex(["control", "mens_email", "womens_email"])
        .reset_index()
    )
    fig, axes = plt.subplots(1, 3, figsize=(17, 5))
    columns = ["visit_rate", "conversion_rate", "revenue_per_user"]
    titles = ["14-day visit rate", "14-day conversion rate", "Revenue per user"]
    for axis, column, title in zip(axes, columns, titles, strict=True):
        values = ordered[column].to_numpy()
        colors = [COLORS[a] for a in ordered["treatment_arm"]]
        bars = axis.bar(ordered["treatment_arm"], values, color=colors, width=0.68)
        axis.set_title(title)
        axis.tick_params(axis="x", rotation=18)
        axis.set_ylabel("rate" if column != "revenue_per_user" else "USD")
        for bar, value in zip(bars, values, strict=True):
            label = f"{value:.2%}" if column != "revenue_per_user" else f"${value:.2f}"
            axis.text(
                bar.get_x() + bar.get_width() / 2,
                value,
                label,
                ha="center",
                va="bottom",
                fontsize=10,
            )
    fig.suptitle("Experiment outcomes by randomized arm", fontsize=18, fontweight="bold")
    fig.tight_layout()
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)
    return output


def plot_balance(
    balance: pd.DataFrame, output: Path = FIGURE_DIR / "covariate_balance.png"
) -> Path:
    set_plot_style()
    top = (
        balance.sort_values("absolute_smd", ascending=False)
        .groupby("comparison", as_index=False, group_keys=False)
        .head(12)
        .copy()
    )
    fig, axis = plt.subplots(figsize=(12, 8))
    sns.scatterplot(
        data=top,
        x="smd",
        y="covariate",
        hue="comparison",
        s=90,
        ax=axis,
    )
    axis.axvline(-0.10, color="#DC2626", linestyle="--", linewidth=1.2)
    axis.axvline(0.10, color="#DC2626", linestyle="--", linewidth=1.2)
    axis.axvline(0, color="#111827", linewidth=1)
    axis.set_title("Pre-treatment covariate balance")
    axis.set_xlabel("Standardized mean difference")
    axis.set_ylabel("")
    axis.legend(title="Comparison", loc="lower right")
    fig.tight_layout()
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)
    return output


def plot_power(
    power: pd.DataFrame, output: Path = FIGURE_DIR / "minimum_detectable_effect.png"
) -> Path:
    set_plot_style()
    data = power.copy()
    data["label"] = data["comparison"] + "\n" + data["outcome"]
    fig, axis = plt.subplots(figsize=(12, 6))
    bars = axis.bar(
        data["label"],
        100 * data["mde_absolute"],
        color=[COLORS.get(value.split("_vs_")[0], "#2563EB") for value in data["comparison"]],
    )
    axis.set_title("Minimum detectable absolute lift at 80% power")
    axis.set_ylabel("Percentage points")
    axis.tick_params(axis="x", rotation=15)
    for bar, value in zip(bars, data["mde_absolute"], strict=True):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            100 * value,
            f"{100 * value:.2f} pp",
            ha="center",
            va="bottom",
            fontsize=10,
        )
    fig.tight_layout()
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)
    return output


def plot_qini(curves: pd.DataFrame, output: Path = FIGURE_DIR / "qini_curves.png") -> Path:
    set_plot_style()
    fig, axis = plt.subplots(figsize=(11, 7))
    for model, subset in curves.groupby("model"):
        step = max(1, len(subset) // 500)
        sampled = subset.iloc[::step]
        axis.plot(
            sampled["targeted_fraction"],
            sampled["qini"],
            label=model,
            color=COLORS.get(model),
            linewidth=2.3,
        )
    baseline = curves[curves["model"].eq(curves["model"].iloc[0])]
    axis.plot(
        baseline["targeted_fraction"],
        baseline["random_baseline"],
        color="#6B7280",
        linestyle="--",
        label="random targeting",
    )
    axis.set_title("Held-out test Qini curves")
    axis.set_xlabel("Targeted population fraction")
    axis.set_ylabel("Cumulative incremental visits")
    axis.legend()
    fig.tight_layout()
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)
    return output


def plot_policy(policy: pd.DataFrame, output: Path = FIGURE_DIR / "policy_value.png") -> Path:
    set_plot_style()
    if "evaluation_split" in policy:
        validation = policy[policy["evaluation_split"].eq("validation")]
        test = policy[policy["evaluation_split"].eq("test")]
    else:
        validation = policy
        test = pd.DataFrame()

    selected = validation.loc[validation["estimated_net_value"].idxmax()]
    selected_fraction = float(selected["targeted_fraction"])
    heldout = (
        test.loc[np.isclose(test["targeted_fraction"], selected_fraction)].iloc[0]
        if not test.empty
        else selected
    )

    fig, axis = plt.subplots(figsize=(11, 7))
    axis.plot(
        validation["targeted_fraction"],
        validation["estimated_net_value"],
        color="#7C3AED",
        linewidth=2.6,
        label="validation (policy selection)",
    )
    if not test.empty:
        axis.plot(
            test["targeted_fraction"],
            test["estimated_net_value"],
            color="#0F766E",
            linewidth=2.2,
            label="held-out test (evaluation only)",
        )
    axis.scatter(
        [heldout["targeted_fraction"]],
        [heldout["estimated_net_value"]],
        color="#DC2626",
        s=100,
        zorder=5,
    )
    axis.axvline(selected_fraction, color="#DC2626", linestyle="--", linewidth=1.2)
    axis.annotate(
        f"Selected on validation: {selected_fraction:.0%}",
        (heldout["targeted_fraction"], heldout["estimated_net_value"]),
        xytext=(12, 18),
        textcoords="offset points",
    )
    axis.axhline(0, color="#111827", linewidth=1)
    axis.set_title("Offline policy value with honest selection/evaluation split")
    axis.set_xlabel("Targeted population fraction")
    axis.set_ylabel("Estimated net value (USD)")
    axis.legend()
    fig.tight_layout()
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)
    return output


def _format_lift(row: pd.Series) -> str:
    if "rate" in str(row["outcome"]):
        return f"{100 * row['absolute_lift']:.2f} percentage points"
    return f"${row['absolute_lift']:.3f} per user"


def generate_decision_memo(
    output: Path,
    arm_metrics: pd.DataFrame,
    srm: dict[str, float | bool],
    balance: pd.DataFrame,
    tests: pd.DataFrame,
    power: pd.DataFrame,
    cuped: pd.DataFrame,
    model_comparison: pd.DataFrame,
    policy: pd.DataFrame,
    best_model: str,
    synthetic: bool,
) -> Path:
    mens = tests[tests["comparison"].eq("mens_email_vs_control")]
    validation_policy = policy[policy["evaluation_split"].eq("validation")]
    test_policy = policy[policy["evaluation_split"].eq("test")]
    best_policy = validation_policy.loc[validation_policy["estimated_net_value"].idxmax()]
    selected_fraction = float(best_policy["targeted_fraction"])
    heldout_policy = test_policy.loc[
        np.isclose(test_policy["targeted_fraction"], selected_fraction)
    ].iloc[0]
    max_smd = float(balance["absolute_smd"].max())
    lines = [
        "# Experiment decision memo",
        "",
        f"> Data mode: **{'synthetic smoke test' if synthetic else 'public Hillstrom randomized experiment'}**.",
        "",
        "## Executive decision",
        "",
    ]
    revenue_row = mens[mens["outcome"].eq("revenue_per_user")].iloc[0]
    decision = (
        "launch the men's creative for the studied population"
        if revenue_row["reject_h0_bh"] and revenue_row["absolute_lift"] > 0
        else "do not launch without more evidence"
    )
    lines.append(
        f"The pre-registered primary metric supports the decision to **{decision}**. "
        "This conclusion applies to customers active in the prior 12 months and the two-week measurement window."
    )
    lines.extend(
        [
            "",
            "## Experiment validity",
            "",
            f"- SRM p-value: `{float(srm['p_value']):.4f}`; SRM detected: `{bool(srm['srm_detected'])}`.",
            f"- Maximum absolute standardized mean difference: `{max_smd:.3f}` (rule-of-thumb threshold: 0.10).",
            "- Treatment assignment is analyzed concurrently, not as a before/after comparison.",
            "",
            "## Average treatment effects: men's email versus control",
            "",
        ]
    )
    for _, row in mens.iterrows():
        lines.append(
            f"- **{row['outcome']}**: {_format_lift(row)}; "
            f"95% CI [{row['ci_low']:.4f}, {row['ci_high']:.4f}], "
            f"BH-adjusted p = {row['p_value_bh']:.4g}."
        )
    lines.extend(
        [
            "",
            "## Power and variance reduction",
            "",
        ]
    )
    for _, row in power[power["comparison"].eq("mens_email_vs_control")].iterrows():
        lines.append(
            f"- {row['outcome']}: detectable absolute lift `{100 * row['mde_absolute']:.2f} pp` "
            f"at {row['target_power']:.0%} power."
        )
    lines.append(
        f"- CUPED variance reduction ranged from `{cuped['variance_reduction'].min():.2%}` "
        f"to `{cuped['variance_reduction'].max():.2%}`. A weak result is reported rather than hidden."
    )
    lines.extend(
        [
            "",
            "## Heterogeneous treatment effects",
            "",
            f"- Model selected on validation Qini: **{best_model}**.",
            f"- Held-out test Qini coefficient: `{float(model_comparison.loc[model_comparison['model'].eq(best_model), 'test_qini'].iloc[0]):.5f}`.",
            f"- Under the illustrative economics (${best_policy['value_per_incremental_outcome']:.2f} per incremental visit and ${best_policy['cost_per_contact']:.2f} total contact/opportunity cost), validation selects {selected_fraction:.0%} of eligible users; the fixed policy has held-out test net value ${heldout_policy['estimated_net_value']:,.2f}.",
            "- The economics are a scenario, not observed profit. Re-estimate them before any production decision.",
            "",
            "## Limitations",
            "",
            "1. The public experiment is historical email data; the method transfers, but the effect size does not automatically transfer to a content platform.",
            "2. Outcomes cover two weeks and miss delayed behavior.",
            "3. Uplift is modeled on visits because conversion is sparse; conversion and revenue remain business outcomes, not interchangeable labels.",
            "4. Offline policy value requires a prospective randomized holdout before deployment.",
            "",
            "## Reproducibility",
            "",
            "All metrics were generated by `python scripts/run_pipeline.py`. Raw data and model binaries are excluded from Git; summary tables and figures are versionable.",
        ]
    )
    output.write_text("\n".join(lines), encoding="utf-8")
    return output
