"""DuckDB data mart construction and query helpers."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from growth_lab.config import DATABASE_PATH, SQL_DIR, ensure_directories


def build_database(frame: pd.DataFrame, database_path: Path = DATABASE_PATH) -> Path:
    """Build normalized experiment tables and reusable metric views."""
    ensure_directories()
    connection = duckdb.connect(str(database_path))
    try:
        connection.register("source_frame", frame)
        connection.execute((SQL_DIR / "01_build_mart.sql").read_text(encoding="utf-8"))
    finally:
        connection.close()
    return database_path


def query_frame(sql: str, database_path: Path = DATABASE_PATH) -> pd.DataFrame:
    with duckdb.connect(str(database_path), read_only=True) as connection:
        return connection.execute(sql).fetchdf()


def experiment_frame(database_path: Path = DATABASE_PATH) -> pd.DataFrame:
    return query_frame("SELECT * FROM experiment_analysis ORDER BY customer_id", database_path)


def arm_metrics(database_path: Path = DATABASE_PATH) -> pd.DataFrame:
    return query_frame("SELECT * FROM arm_metrics ORDER BY treatment_arm", database_path)


def data_quality_summary(database_path: Path = DATABASE_PATH) -> pd.DataFrame:
    return query_frame("SELECT * FROM data_quality_summary ORDER BY check_name", database_path)
