from pathlib import Path

import pandas as pd


class ETLProcessor:
	CHARACTER_COLUMNS = [
		"source_id",
		"name",
		"race",
		"background",
		"total_level",
		"hp",
		"str",
		"dex",
		"con",
		"int",
		"wis",
		"cha",
		"notes_len",
		"recorded_at",
	]

	NUMERIC_CHARACTER_COLUMNS = ["total_level", "hp", "str", "dex", "con", "int", "wis", "cha", "notes_len"]

	def __init__(self, data_dir: str | None = None) -> None:
		base_dir = Path(__file__).resolve().parent
		self.data_dir = Path(data_dir) if data_dir is not None else (base_dir / ".." / "data")
		self.over_one_mil_csv = self.data_dir / "over_one_mil_chars.csv"
		self.dnd_chars_csv = self.data_dir / "dnd_chars_all.csv"

	def run_pipeline(self, sample_rows: int | None = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
		over_one_mil_df, dnd_chars_df = self.extract_source_dataframes(sample_rows=sample_rows)

		over_one_mil_df, removed_rows = self.remove_incomplete_character_names(over_one_mil_df)
		character_df = self.build_character_table_df(over_one_mil_df)

		class_df = self.build_character_class_table_df(over_one_mil_df)
		class_counts = class_df.groupby("source_id").size()
		multiclass_ids = class_counts[class_counts > 1].index
		character_df["is_multiclass"] = character_df["source_id"].isin(multiclass_ids)
		multiclass_df = class_df[class_df["source_id"].isin(multiclass_ids)]
		return character_df, class_df, dnd_chars_df

	def run(self, sample_rows: int | None = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
		"""Backward-compatible wrapper."""
		return self.run_pipeline(sample_rows=sample_rows)

	def remove_incomplete_character_names(self, over_one_mil_df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
		bad_names = over_one_mil_df["name"].fillna("").str.contains(r"['’]s character", case=False, regex=True)
		removed_rows = int(bad_names.sum())
		return over_one_mil_df.loc[~bad_names].copy(), removed_rows

	def build_character_table_df(self, over_one_mil_df: pd.DataFrame) -> pd.DataFrame:
		rename_map = {
			"char_id": "source_id",
			"base_hp": "hp",
			"stats_1": "str",
			"stats_2": "dex",
			"stats_3": "con",
			"stats_4": "int",
			"stats_5": "wis",
			"stats_6": "cha",
			"date_modified": "recorded_at",
		}

		character_df = over_one_mil_df.rename(columns=rename_map).loc[:, self.CHARACTER_COLUMNS].copy()
		character_df["source_id"] = character_df["source_id"].astype("string")
		character_df["recorded_at"] = pd.to_datetime(character_df["recorded_at"], errors="coerce", utc=True)

		for col in self.NUMERIC_CHARACTER_COLUMNS:
			character_df[col] = pd.to_numeric(character_df[col], errors="coerce")

		return character_df

	def build_character_class_table_df(self, over_one_mil_df: pd.DataFrame) -> pd.DataFrame:
		# Starting class rows (always one potential row per character).
		start_df = (
			over_one_mil_df.loc[:, ["char_id", "class_starting", "subclass_starting", "class_starting_level"]]
			.rename(
				columns={
					"char_id": "source_id",
					"class_starting": "class",
					"subclass_starting": "subclass",
					"class_starting_level": "level",
				}
			)
			.copy()
		)

		for col in ["class", "subclass"]:
			start_df[col] = self.normalize_text_series(start_df[col])

		start_df["source_id"] = start_df["source_id"].astype("string")
		start_df["level"] = pd.to_numeric(start_df["level"], errors="coerce")
		start_df = start_df.dropna(subset=["class"])

		# Multiclass rows from slash-delimited fields.
		other_rows: list[dict[str, object]] = []
		other_cols = ["char_id", "class_other", "subclass_other"]
		for row in over_one_mil_df.loc[:, other_cols].itertuples(index=False):
			class_vals = self.split_slash_delimited_values(getattr(row, "class_other"))
			subclass_vals = self.split_slash_delimited_values(getattr(row, "subclass_other"))

			for idx, class_name in enumerate(class_vals):
				subclass_name = subclass_vals[idx] if idx < len(subclass_vals) else pd.NA
				other_rows.append(
					{
						"source_id": str(getattr(row, "char_id")),
						"class": class_name,
						"subclass": subclass_name,
						"level": pd.NA,
					}
				)

		other_df = pd.DataFrame(other_rows, columns=["source_id", "class", "subclass", "level"])

		class_df = pd.concat([start_df, other_df], ignore_index=True)
		class_df["class"] = self.normalize_text_series(class_df["class"])
		class_df["subclass"] = self.normalize_text_series(class_df["subclass"])
		class_df = class_df.dropna(subset=["class"])
		class_df = class_df.drop_duplicates(subset=["source_id", "class", "subclass"], keep="first")
		return class_df

	def normalize_text_series(self, series: pd.Series) -> pd.Series:
		return series.astype("string").str.strip().replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})

	def split_slash_delimited_values(self, value: object) -> list[str]:
		if pd.isna(value):
			return []

		parts = [v.strip() for v in str(value).split("/") if v and v.strip()]
		return [part for part in parts if part.lower() not in {"nan", "none"}]

	def extract_primary_characters_csv(self, sample_rows: int | None = None) -> pd.DataFrame:
		return pd.read_csv(self.over_one_mil_csv, nrows=sample_rows)

	def extract_secondary_characters_csv(self, sample_rows: int | None = None) -> pd.DataFrame:
		return pd.read_csv(self.dnd_chars_csv, nrows=sample_rows)

	def extract_source_dataframes(self, sample_rows: int | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
		over_one_mil_df = self.extract_primary_characters_csv(sample_rows=sample_rows)
		dnd_chars_df = self.extract_secondary_characters_csv(sample_rows=sample_rows)
		return over_one_mil_df, dnd_chars_df

	def drop_incomplete_names(self, over_one_mil_df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
		"""Backward-compatible wrapper."""
		return self.remove_incomplete_character_names(over_one_mil_df)

	def build_character_df(self, over_one_mil_df: pd.DataFrame) -> pd.DataFrame:
		"""Backward-compatible wrapper."""
		return self.build_character_table_df(over_one_mil_df)

	def build_character_class_df(self, over_one_mil_df: pd.DataFrame) -> pd.DataFrame:
		"""Backward-compatible wrapper."""
		return self.build_character_class_table_df(over_one_mil_df)

	def normalize_text(self, series: pd.Series) -> pd.Series:
		"""Backward-compatible wrapper."""
		return self.normalize_text_series(series)

	def split_slash_field(self, value: object) -> list[str]:
		"""Backward-compatible wrapper."""
		return self.split_slash_delimited_values(value)

	def extract_over_one_mil(self, sample_rows: int | None = None) -> pd.DataFrame:
		"""Backward-compatible wrapper."""
		return self.extract_primary_characters_csv(sample_rows=sample_rows)

	def extract_dnd_chars(self, sample_rows: int | None = None) -> pd.DataFrame:
		"""Backward-compatible wrapper."""
		return self.extract_secondary_characters_csv(sample_rows=sample_rows)

	def extract_all(self, sample_rows: int | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
		"""Backward-compatible wrapper."""
		return self.extract_source_dataframes(sample_rows=sample_rows)


if __name__ == "__main__":
	ETLProcessor().run_pipeline()
