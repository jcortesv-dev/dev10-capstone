from pathlib import Path

import pandas as pd

from extract import extract_primary_dataframe
from transform import transform_primary


class ETLProcessor:
    def __init__(self, data_dir: str | None = None) -> None:
        base_dir = Path(__file__).resolve().parent
        self.data_dir = Path(data_dir) if data_dir is not None else (base_dir / ".." / "data")

    def run(self, sample_rows: int | None = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        primary_df = extract_primary_dataframe(self.data_dir, sample_rows=sample_rows)
        character_df, class_df, feat_df = transform_primary(primary_df)
        return character_df, class_df, feat_df
