from pathlib import Path

import pandas as pd


def extract_primary_dataframe(data_dir: Path, sample_rows: int | None = None) -> pd.DataFrame:
    primary_csv = data_dir / "over_one_mil_chars.csv"
    return pd.read_csv(primary_csv, nrows=sample_rows)
