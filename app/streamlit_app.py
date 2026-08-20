"""Interactive stakeholder dashboard for the generated experiment artifacts."""

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from growth_lab.uplift import policy_value_curve  # noqa: E402

METRICS = ROOT / "artifacts" / "metrics"
FIGURES = ROOT / "artifacts" / "figures"

st.set_page_config(
    page_title="Growth Experimentation Lab",
    page_icon="📈",
    layout="wide",
)


@st.cache_data
def load_csv(name: str) -> pd.DataFrame:
    path = METRICS / name
    if not path.exists():
        st.error("Artifacts are missing. Run `python scripts/run_pipeline.py` first.")
        st.stop()
    return pd.read_csv(path)


def show_image(name: str, caption: str) -> None:
    path = FIGURES / name
    if path.exists():
        st.image(str(path), caption=caption, use_container_width=True)


st.title("Growth Experimentation & Causal Uplift Lab")
st.caption(
    "A reproducible three-arm randomized experiment, from validity checks to an offline targeting policy."
)

arms = load_csv("arm_metrics.csv")
tests = load_csv("pairwise_tests.csv")
balance = load_csv("covariate_balance.csv")
srm = load_csv("srm_test.csv").iloc[0]
power = load_csv("power_analysis.csv")
cuped = load_csv("cuped_results.csv")
models = load_csv("uplift_model_comparison.csv")
scored_validation = load_csv("scored_validation_sample.csv")
scored_test = load_csv("scored_test_sample.csv")

overview_tab, validity_tab, inference_tab, uplift_tab, reproducibility_tab = st.tabs(
    ["Decision", "Validity", "Inference", "Uplift & policy", "Reproducibility"]
)

with overview_tab:
    control = arms[arms["treatment_arm"].eq("control")].iloc[0]
    mens = arms[arms["treatment_arm"].eq("mens_email")].iloc[0]
    columns = st.columns(4)
    columns[0].metric("Users", f"{int(arms['users'].sum()):,}")
    columns[1].metric(
        "Visit lift",
        f"{100 * (mens['visit_rate'] - control['visit_rate']):.2f} pp",
    )
    columns[2].metric(
        "Conversion lift",
        f"{100 * (mens['conversion_rate'] - control['conversion_rate']):.2f} pp",
    )
    columns[3].metric(
        "Revenue lift / user",
        f"${mens['revenue_per_user'] - control['revenue_per_user']:.3f}",
    )
    st.info(
        "Decision rule: use revenue per user as the primary business metric; visits and conversion are diagnostics."
    )
    show_image("arm_metrics.png", "Randomized-arm outcome comparison")

with validity_tab:
    col1, col2, col3 = st.columns(3)
    col1.metric("SRM p-value", f"{float(srm['p_value']):.4f}")
    col2.metric("SRM detected", str(bool(srm["srm_detected"])))
    col3.metric("Max |SMD|", f"{balance['absolute_smd'].max():.3f}")
    st.markdown(
        "A valid readout requires the executed arm ratio to match the planned split and all pre-treatment covariates to be balanced."
    )
    show_image("covariate_balance.png", "Standardized mean differences; dashed lines mark ±0.10")
    st.dataframe(balance, use_container_width=True, hide_index=True)

with inference_tab:
    comparison = st.selectbox("Comparison", tests["comparison"].unique())
    filtered = tests[tests["comparison"].eq(comparison)].copy()
    st.dataframe(
        filtered[
            [
                "outcome",
                "mean_treatment",
                "mean_control",
                "absolute_lift",
                "ci_low",
                "ci_high",
                "p_value_bh",
                "reject_h0_bh",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )
    left, right = st.columns(2)
    with left:
        show_image("minimum_detectable_effect.png", "Observed-design MDE")
    with right:
        st.subheader("CUPED")
        st.dataframe(
            cuped[["method", "comparison", "adjusted_lift", "variance_reduction", "p_value"]],
            use_container_width=True,
            hide_index=True,
        )
        st.caption(
            "Low variance reduction is a valid finding when pre-period covariates weakly predict the outcome."
        )
    with st.expander("Power table"):
        st.dataframe(power, use_container_width=True, hide_index=True)

with uplift_tab:
    selected = models.sort_values("validation_qini", ascending=False).iloc[0]
    st.success(
        f"Selected on validation data: {selected['model']} | held-out test Qini: {selected['test_qini']:.5f}"
    )
    st.dataframe(models, use_container_width=True, hide_index=True)
    show_image("qini_curves.png", "Model ranking quality on the untouched test set")

    st.subheader("Policy economics simulator")
    value = st.slider(
        "Value per incremental visit (scenario, USD)",
        min_value=0.50,
        max_value=20.00,
        value=5.00,
        step=0.50,
    )
    cost = st.slider(
        "Contact + opportunity cost per user (scenario, USD)",
        min_value=0.00,
        max_value=2.00,
        value=0.50,
        step=0.05,
        help="Includes delivery cost and the opportunity cost of a limited contact slot; it is not observed profit.",
    )
    validation_policy = policy_value_curve(
        scored_validation["outcome"].to_numpy(),
        scored_validation["treatment"].to_numpy(),
        scored_validation["uplift_score"].to_numpy(),
        value_per_incremental_outcome=value,
        contact_cost=cost,
    )
    selected = validation_policy.loc[validation_policy["estimated_net_value"].idxmax()]
    selected_fraction = float(selected["targeted_fraction"])

    test_policy = policy_value_curve(
        scored_test["outcome"].to_numpy(),
        scored_test["treatment"].to_numpy(),
        scored_test["uplift_score"].to_numpy(),
        value_per_incremental_outcome=value,
        contact_cost=cost,
    )
    heldout = test_policy.loc[
        test_policy["targeted_fraction"].sub(selected_fraction).abs().idxmin()
    ]

    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Selected target share", f"{selected_fraction:.0%}")
    p2.metric("Validation net value", f"${selected['estimated_net_value']:,.0f}")
    p3.metric("Held-out incremental visits", f"{heldout['estimated_incremental_outcomes']:.1f}")
    p4.metric("Held-out net value", f"${heldout['estimated_net_value']:,.0f}")

    chart = pd.concat(
        [
            validation_policy.assign(split="validation"),
            test_policy.assign(split="held-out test"),
        ],
        ignore_index=True,
    )
    st.line_chart(
        chart.pivot(
            index="targeted_fraction",
            columns="split",
            values="estimated_net_value",
        ),
        use_container_width=True,
    )
    st.caption(
        "The target share is selected on validation data. Test outcomes only evaluate that fixed share."
    )
    st.warning(
        "This is an offline scenario. A prospective randomized holdout is required before deployment."
    )

with reproducibility_tab:
    manifest_path = ROOT / "artifacts" / "run_manifest.json"
    if manifest_path.exists():
        st.json(json.loads(manifest_path.read_text(encoding="utf-8")))
    st.markdown(
        """
        **Reproduce**

        ```powershell
        python -m venv .venv
        .\\.venv\\Scripts\\python.exe -m pip install -e ".[dev]"
        .\\.venv\\Scripts\\python.exe scripts\\run_pipeline.py
        .\\.venv\\Scripts\\streamlit.exe run app\\streamlit_app.py
        ```

        The raw dataset and serialized model are deliberately excluded from Git.
        Generated metrics, figures, and the decision memo provide an auditable result trail.
        """
    )
