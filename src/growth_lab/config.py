"""Central paths and reproducibility settings."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
SQL_DIR = PROJECT_ROOT / "sql"
ARTIFACT_DIR = PROJECT_ROOT / "artifacts"
METRIC_DIR = ARTIFACT_DIR / "metrics"
FIGURE_DIR = ARTIFACT_DIR / "figures"
MODEL_DIR = PROJECT_ROOT / "models"

RAW_GZIP_PATH = RAW_DIR / "hillstrom_no_indices.csv.gz"
CLEAN_DATA_PATH = PROCESSED_DIR / "hillstrom_clean.csv"
DATABASE_PATH = PROCESSED_DIR / "growth_lab.duckdb"

HILLSTROM_URL = "https://hillstorm1.s3.us-east-2.amazonaws.com/hillstorm_no_indices.csv.gz"
HILLSTROM_MD5 = "a68a81291f53a14f4e29002629803ba3"

RANDOM_SEED = 20260820
CONTROL_ARM = "control"
TREATMENT_ARMS = ("mens_email", "womens_email")
ALL_ARMS = (CONTROL_ARM, *TREATMENT_ARMS)


def ensure_directories() -> None:
    """Create all runtime output directories."""
    for path in (
        RAW_DIR,
        PROCESSED_DIR,
        METRIC_DIR,
        FIGURE_DIR,
        MODEL_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)
