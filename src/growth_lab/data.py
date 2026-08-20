"""Download, validate, and normalize the Hillstrom randomized experiment."""

from __future__ import annotations

import hashlib
import shutil
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from growth_lab.config import (
    CLEAN_DATA_PATH,
    HILLSTROM_MD5,
    HILLSTROM_URL,
    RANDOM_SEED,
    RAW_GZIP_PATH,
    ensure_directories,
)

EXPECTED_COLUMNS = {
    "recency",
    "history_segment",
    "history",
    "mens",
    "womens",
    "zip_code",
    "newbie",
    "channel",
    "segment",
    "visit",
    "conversion",
    "spend",
}

SEGMENT_MAP = {
    "No E-Mail": "control",
    "Mens E-Mail": "mens_email",
    "Womens E-Mail": "womens_email",
    "no e-mail": "control",
    "mens e-mail": "mens_email",
    "womens e-mail": "womens_email",
}


def file_md5(path: Path) -> str:
    digest = hashlib.md5()  # noqa: S324 - upstream publishes an MD5 integrity hash
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_hillstrom(destination: Path = RAW_GZIP_PATH, force: bool = False) -> Path:
    """Download the public dataset mirror and verify its published checksum."""
    ensure_directories()
    if destination.exists() and not force:
        if file_md5(destination) == HILLSTROM_MD5:
            return destination
        destination.unlink()

    request = urllib.request.Request(
        HILLSTROM_URL,
        headers={"User-Agent": "growth-experimentation-lab/0.1"},
    )
    temporary = destination.with_suffix(destination.suffix + ".part")
    with urllib.request.urlopen(request, timeout=90) as response:  # noqa: S310
        with temporary.open("wb") as output:
            shutil.copyfileobj(response, output)

    actual_hash = file_md5(temporary)
    if actual_hash != HILLSTROM_MD5:
        temporary.unlink(missing_ok=True)
        raise ValueError(f"Dataset checksum mismatch: expected {HILLSTROM_MD5}, got {actual_hash}.")
    temporary.replace(destination)
    return destination


def _snake_case_columns(frame: pd.DataFrame) -> pd.DataFrame:
    renamed = {column: column.strip().lower().replace(" ", "_") for column in frame.columns}
    return frame.rename(columns=renamed)


def normalize_hillstrom(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a typed, analysis-ready copy with stable identifiers."""
    clean = _snake_case_columns(frame.copy())
    missing = EXPECTED_COLUMNS - set(clean.columns)
    if missing:
        raise ValueError(f"Missing expected columns: {sorted(missing)}")

    clean["treatment_arm"] = clean["segment"].replace(SEGMENT_MAP)
    if clean["treatment_arm"].isin({"control", "mens_email", "womens_email"}).mean() != 1:
        unknown = sorted(
            clean.loc[
                ~clean["treatment_arm"].isin({"control", "mens_email", "womens_email"}), "segment"
            ]
            .astype(str)
            .unique()
        )
        raise ValueError(f"Unknown treatment labels: {unknown}")

    clean = clean.drop(columns=["segment"]).reset_index(drop=True)
    clean.insert(0, "customer_id", np.arange(1, len(clean) + 1, dtype=np.int64))
    clean["is_treated"] = (clean["treatment_arm"] != "control").astype("int8")

    integer_columns = ["recency", "mens", "womens", "newbie", "visit", "conversion"]
    for column in integer_columns:
        clean[column] = pd.to_numeric(clean[column], errors="raise").astype("int64")
    clean["history"] = pd.to_numeric(clean["history"], errors="raise").astype("float64")
    clean["spend"] = pd.to_numeric(clean["spend"], errors="raise").astype("float64")
    for column in ["history_segment", "zip_code", "channel", "treatment_arm"]:
        clean[column] = clean[column].astype("string")

    validate_hillstrom(clean)
    return clean


def validate_hillstrom(frame: pd.DataFrame, require_real_size: bool = True) -> None:
    """Fail fast on schema violations that would invalidate the experiment."""
    if require_real_size and len(frame) != 64_000:
        raise ValueError(f"Expected 64,000 rows, received {len(frame):,}.")
    if not frame["customer_id"].is_unique:
        raise ValueError("customer_id must be unique.")
    if frame.isna().any().any():
        nulls = frame.isna().sum()
        raise ValueError(f"Unexpected missing values: {nulls[nulls > 0].to_dict()}")
    for column in ["mens", "womens", "newbie", "visit", "conversion", "is_treated"]:
        if not set(frame[column].unique()).issubset({0, 1}):
            raise ValueError(f"{column} is not binary.")
    if (frame[["history", "spend"]] < 0).any().any():
        raise ValueError("history and spend must be non-negative.")
    if set(frame["treatment_arm"].unique()) != {
        "control",
        "mens_email",
        "womens_email",
    }:
        raise ValueError("All three randomized arms must be present.")


def generate_synthetic_experiment(n: int = 12_000, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Generate a deterministic smoke-test dataset; never use it for resume claims."""
    rng = np.random.default_rng(seed)
    recency = rng.integers(1, 13, n)
    history = np.clip(rng.gamma(shape=2.0, scale=140.0, size=n), 5, 1_500)
    mens = rng.binomial(1, 0.45, n)
    womens = rng.binomial(1, 0.55, n)
    newbie = rng.binomial(1, 0.40, n)
    zip_code = rng.choice(["Urban", "Suburban", "Rural"], n, p=[0.45, 0.35, 0.20])
    channel = rng.choice(["Web", "Phone", "Multichannel"], n, p=[0.50, 0.30, 0.20])
    arm = rng.choice(["control", "mens_email", "womens_email"], n)

    baseline_visit = 0.08 + 0.035 * (recency <= 3) + 0.02 * (channel == "Web")
    visit_lift = (
        0.075 * (arm == "mens_email")
        + 0.045 * (arm == "womens_email")
        + 0.025 * (arm == "mens_email") * mens
    )
    visit = rng.binomial(1, np.clip(baseline_visit + visit_lift, 0.001, 0.95))

    baseline_conversion = 0.004 + 0.002 * (history > 300)
    conversion_lift = 0.006 * (arm == "mens_email") + 0.003 * (arm == "womens_email")
    conversion = rng.binomial(
        1,
        np.clip((baseline_conversion + conversion_lift) * (0.4 + 0.6 * visit), 0.0001, 0.2),
    )
    spend = conversion * rng.gamma(shape=2.2, scale=48.0, size=n)

    history_segment = pd.cut(
        history,
        bins=[-np.inf, 100, 200, 350, 500, 750, 1_000, np.inf],
        labels=[
            "$0-$100",
            "$100-$200",
            "$200-$350",
            "$350-$500",
            "$500-$750",
            "$750-$1,000",
            "$1,000+",
        ],
    ).astype(str)

    frame = pd.DataFrame(
        {
            "customer_id": np.arange(1, n + 1),
            "recency": recency,
            "history_segment": history_segment,
            "history": history,
            "mens": mens,
            "womens": womens,
            "zip_code": zip_code,
            "newbie": newbie,
            "channel": channel,
            "visit": visit,
            "conversion": conversion,
            "spend": spend,
            "treatment_arm": arm,
            "is_treated": (arm != "control").astype(int),
        }
    )
    validate_hillstrom(frame, require_real_size=False)
    return frame


def prepare_data(
    force_download: bool = False,
    use_synthetic: bool = False,
    output_path: Path = CLEAN_DATA_PATH,
) -> pd.DataFrame:
    """Materialize the clean CSV and return the analysis frame."""
    ensure_directories()
    if output_path.exists() and not force_download and not use_synthetic:
        clean = pd.read_csv(output_path)
        clean["treatment_arm"] = clean["treatment_arm"].astype("string")
        validate_hillstrom(clean)
        return clean

    if use_synthetic:
        clean = generate_synthetic_experiment()
    else:
        source = download_hillstrom(force=force_download)
        clean = normalize_hillstrom(pd.read_csv(source, compression="gzip"))

    clean.to_csv(output_path, index=False)
    return clean
