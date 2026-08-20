"""Generate the publication-style framework diagram for the project.

The schematic is intentionally data-light: it communicates the evidence flow,
the strict train/validation/test contract, and the boundary between offline
policy value and production impact.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch

PALETTE = {
    "ink": "#172033",
    "muted": "#5F6878",
    "border": "#D6DDE8",
    "soft_gray": "#F5F7FA",
    "blue": "#2767D8",
    "blue_soft": "#EAF0FC",
    "teal": "#208B83",
    "teal_soft": "#E8F5F3",
    "violet": "#735BB7",
    "violet_soft": "#F1EDF9",
    "magenta": "#C43E73",
    "magenta_soft": "#FAEAF1",
    "green": "#278A5B",
    "green_soft": "#E8F5ED",
    "white": "#FFFFFF",
}

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "font.size": 7.0,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "axes.linewidth": 0.8,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
    }
)


def rounded_box(
    ax: plt.Axes,
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    facecolor: str,
    edgecolor: str,
    linewidth: float = 0.9,
    radius: float = 0.018,
    zorder: int = 2,
) -> FancyBboxPatch:
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle=f"round,pad=0.006,rounding_size={radius}",
        linewidth=linewidth,
        edgecolor=edgecolor,
        facecolor=facecolor,
        transform=ax.transAxes,
        clip_on=False,
        zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def draw_stage(
    ax: plt.Axes,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    number: int,
    phase: str,
    title: str,
    bullets: tuple[str, str, str],
    metric: str,
    color: str,
    soft_color: str,
) -> None:
    rounded_box(
        ax,
        x,
        y,
        width,
        height,
        facecolor=PALETTE["white"],
        edgecolor=PALETTE["border"],
        linewidth=0.9,
        radius=0.014,
        zorder=3,
    )

    ax.add_patch(
        FancyBboxPatch(
            (x, y + height - 0.054),
            width,
            0.054,
            boxstyle="round,pad=0.006,rounding_size=0.014",
            linewidth=0,
            facecolor=soft_color,
            transform=ax.transAxes,
            zorder=4,
        )
    )
    ax.add_patch(
        FancyBboxPatch(
            (x, y + height - 0.054),
            width,
            0.027,
            boxstyle="square,pad=0",
            linewidth=0,
            facecolor=soft_color,
            transform=ax.transAxes,
            zorder=4,
        )
    )

    circle_x = x + 0.022
    circle_y = y + height - 0.027
    ax.add_patch(
        Circle(
            (circle_x, circle_y),
            0.014,
            facecolor=color,
            edgecolor="none",
            transform=ax.transAxes,
            zorder=5,
        )
    )
    ax.text(
        circle_x,
        circle_y,
        str(number),
        ha="center",
        va="center",
        fontsize=6.0,
        fontweight="bold",
        color=PALETTE["white"],
        transform=ax.transAxes,
        zorder=6,
    )
    ax.text(
        x + 0.043,
        circle_y,
        phase.upper(),
        ha="left",
        va="center",
        fontsize=5.7,
        fontweight="bold",
        color=color,
        transform=ax.transAxes,
        zorder=6,
    )

    ax.text(
        x + 0.014,
        y + height - 0.078,
        title,
        ha="left",
        va="top",
        fontsize=8.0,
        fontweight="bold",
        color=PALETTE["ink"],
        linespacing=1.08,
        transform=ax.transAxes,
        zorder=6,
    )

    bullet_y = y + height - 0.164
    for index, bullet in enumerate(bullets):
        ax.text(
            x + 0.014,
            bullet_y - index * 0.043,
            f"• {bullet}",
            ha="left",
            va="top",
            fontsize=6.15,
            color=PALETTE["muted"],
            transform=ax.transAxes,
            zorder=6,
        )

    rounded_box(
        ax,
        x + 0.011,
        y + 0.014,
        width - 0.022,
        0.052,
        facecolor=soft_color,
        edgecolor="none",
        linewidth=0,
        radius=0.012,
        zorder=4,
    )
    ax.text(
        x + width / 2,
        y + 0.040,
        metric,
        ha="center",
        va="center",
        fontsize=6.0,
        fontweight="bold",
        color=color,
        transform=ax.transAxes,
        zorder=6,
    )


def build_figure() -> plt.Figure:
    fig, ax = plt.subplots(figsize=(7.25, 4.15))
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.025,
        0.956,
        "Growth experimentation and causal uplift decision system",
        ha="left",
        va="top",
        fontsize=13.0,
        fontweight="bold",
        color=PALETTE["ink"],
        transform=ax.transAxes,
    )
    ax.text(
        0.025,
        0.902,
        "From randomized evidence to a cost-aware targeting policy — with a strict held-out evaluation boundary",
        ha="left",
        va="top",
        fontsize=7.2,
        color=PALETTE["muted"],
        transform=ax.transAxes,
    )
    rounded_box(
        ax,
        0.858,
        0.915,
        0.117,
        0.036,
        facecolor=PALETTE["blue_soft"],
        edgecolor="none",
        linewidth=0,
        radius=0.012,
        zorder=2,
    )
    ax.text(
        0.9165,
        0.933,
        "SYSTEM FRAMEWORK",
        ha="center",
        va="center",
        fontsize=5.7,
        fontweight="bold",
        color=PALETTE["blue"],
        transform=ax.transAxes,
        zorder=3,
    )

    margin = 0.025
    gap = 0.014
    width = (1 - 2 * margin - 5 * gap) / 6
    card_y = 0.385
    card_h = 0.405
    x_positions = [margin + index * (width + gap) for index in range(6)]

    group_x = x_positions[3] - 0.009
    group_width = 1 - margin - group_x
    rounded_box(
        ax,
        group_x,
        0.325,
        group_width,
        0.515,
        facecolor="#FBF9FE",
        edgecolor="#CFC4E7",
        linewidth=0.9,
        radius=0.018,
        zorder=0,
    )
    ax.text(
        group_x + 0.012,
        0.817,
        "STRICT 60 / 20 / 20 HOLDOUT PROTOCOL",
        ha="left",
        va="center",
        fontsize=5.8,
        fontweight="bold",
        color=PALETTE["violet"],
        transform=ax.transAxes,
        zorder=2,
    )

    stages = (
        {
            "phase": "Input",
            "title": "Randomized\nexperiment",
            "bullets": ("Public 14-day RCT", "Three assignment arms", "MD5 + schema checks"),
            "metric": "n = 64,000 · 3 arms",
            "color": PALETTE["blue"],
            "soft": PALETTE["blue_soft"],
        },
        {
            "phase": "Validity",
            "title": "Metric mart\nand audit",
            "bullets": ("User-grain DuckDB mart", "Assignment integrity", "Pre-treatment balance"),
            "metric": "SRM p=.904 · |SMD|=.016",
            "color": PALETTE["teal"],
            "soft": PALETTE["teal_soft"],
        },
        {
            "phase": "ATE",
            "title": "Average-effect\ninference",
            "bullets": ("Z / Welch + BH", "Power, MDE, CUPED", "Intent-to-treat effects"),
            "metric": "Visit lift +7.66 pp",
            "color": PALETTE["blue"],
            "soft": PALETTE["blue_soft"],
        },
        {
            "phase": "Train 60%",
            "title": "Uplift model\ntraining",
            "bullets": ("Fit on train only", "Visit HTE ranking", "Independent learners"),
            "metric": "S / T / X · Qini / AUUC",
            "color": PALETTE["violet"],
            "soft": PALETTE["violet_soft"],
        },
        {
            "phase": "Validate 20%",
            "title": "Model and policy\nselection",
            "bullets": ("Select by Qini", "Value − contact cost", "Choose target share"),
            "metric": "X-Learner · target 2%",
            "color": PALETTE["violet"],
            "soft": PALETTE["violet_soft"],
        },
        {
            "phase": "Test 20%",
            "title": "Held-out policy\ndecision",
            "bullets": ("Evaluate exactly once", "Top-k incremental effect", "Memo + dashboard"),
            "metric": "Top 10% uplift +12.85 pp",
            "color": PALETTE["magenta"],
            "soft": PALETTE["magenta_soft"],
        },
    )

    for index, (x, stage) in enumerate(zip(x_positions, stages, strict=True), start=1):
        draw_stage(
            ax,
            x=x,
            y=card_y,
            width=width,
            height=card_h,
            number=index,
            phase=stage["phase"],
            title=stage["title"],
            bullets=stage["bullets"],
            metric=stage["metric"],
            color=stage["color"],
            soft_color=stage["soft"],
        )

    arrow_y = card_y + card_h / 2
    for index in range(5):
        start_x = x_positions[index] + width + 0.002
        end_x = x_positions[index + 1] - 0.002
        ax.add_patch(
            FancyArrowPatch(
                (start_x, arrow_y),
                (end_x, arrow_y),
                arrowstyle="-|>",
                mutation_scale=8,
                linewidth=1.0,
                color="#9BA6B6",
                transform=ax.transAxes,
                zorder=2,
            )
        )

    rounded_box(
        ax,
        0.025,
        0.105,
        0.95,
        0.135,
        facecolor=PALETTE["soft_gray"],
        edgecolor=PALETTE["border"],
        linewidth=0.8,
        radius=0.015,
        zorder=1,
    )
    ax.text(
        0.045,
        0.202,
        "REPRODUCIBLE DELIVERY LAYER",
        ha="left",
        va="center",
        fontsize=5.8,
        fontweight="bold",
        color=PALETTE["muted"],
        transform=ax.transAxes,
        zorder=3,
    )

    chips = (
        ("DuckDB + SQL", 0.045, 0.142),
        ("Python package", 0.215, 0.142),
        ("Versioned artifacts", 0.391, 0.142),
        ("Streamlit dashboard", 0.592, 0.142),
        ("Pytest + GitHub Actions", 0.795, 0.142),
    )
    chip_widths = (0.145, 0.15, 0.174, 0.176, 0.157)
    for (label, chip_x, chip_y), chip_width in zip(chips, chip_widths, strict=True):
        rounded_box(
            ax,
            chip_x,
            chip_y,
            chip_width,
            0.043,
            facecolor=PALETTE["white"],
            edgecolor=PALETTE["border"],
            linewidth=0.7,
            radius=0.012,
            zorder=2,
        )
        ax.text(
            chip_x + chip_width / 2,
            chip_y + 0.0215,
            label,
            ha="center",
            va="center",
            fontsize=5.8,
            fontweight="bold",
            color=PALETTE["ink"],
            transform=ax.transAxes,
            zorder=3,
        )

    ax.add_patch(
        FancyArrowPatch(
            (x_positions[5] + width / 2, card_y - 0.004),
            (x_positions[5] + width / 2, 0.245),
            arrowstyle="-|>",
            mutation_scale=8,
            linewidth=1.0,
            color=PALETTE["magenta"],
            transform=ax.transAxes,
            zorder=2,
        )
    )

    ax.text(
        0.025,
        0.055,
        "Boundary: policy metrics are offline estimates; production impact requires a new randomized holdout.",
        ha="left",
        va="center",
        fontsize=5.8,
        color=PALETTE["muted"],
        transform=ax.transAxes,
    )
    ax.text(
        0.975,
        0.055,
        "Public randomized data · ITT estimand · no test-set tuning",
        ha="right",
        va="center",
        fontsize=5.8,
        color=PALETTE["green"],
        fontweight="bold",
        transform=ax.transAxes,
    )
    return fig


def save_figure(fig: plt.Figure, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = output_dir / "framework_overview"
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight", pad_inches=0.04)
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.04)
    fig.savefig(stem.with_suffix(".png"), dpi=600, bbox_inches="tight", pad_inches=0.04)
    fig.savefig(
        stem.with_suffix(".tiff"),
        dpi=600,
        bbox_inches="tight",
        pad_inches=0.04,
        pil_kwargs={"compression": "tiff_lzw"},
    )
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/figures"),
        help="Directory for SVG, PDF, and PNG outputs.",
    )
    args = parser.parse_args()
    save_figure(build_figure(), args.output_dir)


if __name__ == "__main__":
    main()
