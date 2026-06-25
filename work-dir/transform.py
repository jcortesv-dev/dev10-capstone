import pandas as pd


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


def transform_primary(primary_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cleaned = _clean_primary(primary_df)
    character_df = _build_character_df(cleaned)
    class_df = _build_class_df(cleaned)
    feat_df = _build_feat_df(cleaned)

    class_counts = class_df.groupby("source_id").size()
    multiclass_ids = class_counts[class_counts > 1].index
    character_df["is_multiclass"] = character_df["source_id"].isin(multiclass_ids)

    return character_df, class_df, feat_df


def _clean_primary(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()

    cleaned["name"] = _normalize_text_series(cleaned["name"])
    cleaned = cleaned.dropna(subset=["name"])

    bad_names = cleaned["name"].fillna("").str.contains(r"['’]s character", case=False, regex=True)
    cleaned = cleaned.loc[~bad_names].copy()

    if "date_modified" in cleaned.columns:
        cleaned["date_modified"] = pd.to_datetime(cleaned["date_modified"], errors="coerce", utc=True)
        cleaned = cleaned.sort_values(["char_id", "date_modified"]).drop_duplicates(subset=["char_id"], keep="last")
    else:
        cleaned = cleaned.drop_duplicates(subset=["char_id"], keep="first")

    numeric_cols = [
        "total_level",
        "class_starting_level",
        "base_hp",
        "stats_1",
        "stats_2",
        "stats_3",
        "stats_4",
        "stats_5",
        "stats_6",
        "notes_len",
    ]
    for col in numeric_cols:
        if col in cleaned.columns:
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")

    if "base_hp" in cleaned.columns:
        cleaned.loc[cleaned["base_hp"] < 0, "base_hp"] = pd.NA
    if "notes_len" in cleaned.columns:
        cleaned.loc[cleaned["notes_len"] < 0, "notes_len"] = pd.NA
    if "total_level" in cleaned.columns:
        cleaned.loc[(cleaned["total_level"] < 1) | (cleaned["total_level"] > 20), "total_level"] = pd.NA
    if "class_starting_level" in cleaned.columns:
        cleaned.loc[
            (cleaned["class_starting_level"] < 1) | (cleaned["class_starting_level"] > 20),
            "class_starting_level",
        ] = pd.NA

    for col in ["stats_1", "stats_2", "stats_3", "stats_4", "stats_5", "stats_6"]:
        if col in cleaned.columns:
            cleaned.loc[(cleaned[col] < 1) | (cleaned[col] > 30), col] = pd.NA

    return cleaned


def _build_character_df(primary_df: pd.DataFrame) -> pd.DataFrame:
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

    character_df = primary_df.rename(columns=rename_map).loc[:, CHARACTER_COLUMNS].copy()
    character_df["source_id"] = character_df["source_id"].astype("string")
    character_df["recorded_at"] = pd.to_datetime(character_df["recorded_at"], errors="coerce", utc=True)

    for col in ["total_level", "hp", "str", "dex", "con", "int", "wis", "cha", "notes_len"]:
        character_df[col] = pd.to_numeric(character_df[col], errors="coerce")

    return character_df


def _build_class_df(primary_df: pd.DataFrame) -> pd.DataFrame:
    start_df = (
        primary_df.loc[:, ["char_id", "class_starting", "subclass_starting", "class_starting_level"]]
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

    start_df["class"] = _normalize_text_series(start_df["class"])
    start_df["subclass"] = _normalize_text_series(start_df["subclass"])
    start_df["source_id"] = start_df["source_id"].astype("string")
    start_df["level"] = pd.to_numeric(start_df["level"], errors="coerce")
    start_df = start_df.dropna(subset=["class"])

    other_rows: list[dict[str, object]] = []
    for row in primary_df.loc[:, ["char_id", "class_other", "subclass_other"]].itertuples(index=False):
        class_vals = _split_slash_values(getattr(row, "class_other"))
        subclass_vals = _split_slash_values(getattr(row, "subclass_other"))

        for idx, class_name in enumerate(class_vals):
            other_rows.append(
                {
                    "source_id": str(getattr(row, "char_id")),
                    "class": class_name,
                    "subclass": subclass_vals[idx] if idx < len(subclass_vals) else pd.NA,
                    "level": pd.NA,
                }
            )

    other_df = pd.DataFrame(other_rows, columns=["source_id", "class", "subclass", "level"])
    class_df = pd.concat([start_df, other_df], ignore_index=True)

    class_df["class"] = _normalize_text_series(class_df["class"])
    class_df["subclass"] = _normalize_text_series(class_df["subclass"])
    class_df = class_df.dropna(subset=["class"])
    class_df = class_df.drop_duplicates(subset=["source_id", "class", "subclass"], keep="first")

    return class_df


def _build_feat_df(primary_df: pd.DataFrame) -> pd.DataFrame:
    feat_rows: list[dict[str, object]] = []

    for row in primary_df.loc[:, ["char_id", "feats"]].itertuples(index=False):
        feat_vals = _split_slash_values(getattr(row, "feats"))
        for feat_name in feat_vals:
            feat_rows.append(
                {
                    "source_id": str(getattr(row, "char_id")),
                    "feat": feat_name,
                }
            )

    feat_df = pd.DataFrame(feat_rows, columns=["source_id", "feat"])
    feat_df["source_id"] = feat_df["source_id"].astype("string")
    feat_df["feat"] = _normalize_text_series(feat_df["feat"])
    feat_df = feat_df.dropna(subset=["feat"])
    feat_df = feat_df.drop_duplicates(subset=["source_id", "feat"], keep="first")

    return feat_df


def _normalize_text_series(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})


def _split_slash_values(value: object) -> list[str]:
    if pd.isna(value):
        return []

    parts = [v.strip() for v in str(value).split("/") if v and v.strip()]
    return [part for part in parts if part.lower() not in {"nan", "none"}]
