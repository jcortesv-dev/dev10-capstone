import psycopg
import pandas as pd


def _rows(df: pd.DataFrame, columns: list[str]) -> list[tuple]:
    return [
        tuple(None if pd.isna(v) else v for v in row)
        for row in df.loc[:, columns].itertuples(index=False, name=None)
    ]


def _map_source_to_char_id(conn: psycopg.Connection, schema: str) -> pd.DataFrame:
    with conn.cursor() as cur:
        cur.execute(
            f"""
            select source_id, char_id
            from {schema}.character;
            """
        )
        rows = cur.fetchall()
    return pd.DataFrame(rows, columns=["source_id", "char_id"])


def load_to_postgres(
    character_df: pd.DataFrame,
    class_df: pd.DataFrame,
    feat_df: pd.DataFrame,
    connect_config: dict,
    schema: str = "characters",
) -> dict[str, int]:
    """Load transformed dataframes into Postgres schema characters."""

    character_rows = _rows(
        character_df,
        [
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
        ],
    )

    with psycopg.connect(**connect_config) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                truncate table
                    {schema}.character_feats,
                    {schema}.character_class,
                    {schema}.character
                restart identity cascade;
                """
            )

            cur.executemany(
                f"""
                insert into {schema}.character (
                    source_id, name, race, background, total_level, hp, str, dex, con, int, wis, cha, notes_len, recorded_at
                ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """,
                character_rows,
            )

        mapping_df = _map_source_to_char_id(conn, schema)

        class_with_char_id = class_df.merge(mapping_df, on="source_id", how="inner")
        feat_with_char_id = feat_df.merge(mapping_df, on="source_id", how="inner")

        class_rows = _rows(class_with_char_id, ["char_id", "class", "subclass", "level"])
        feat_rows = _rows(feat_with_char_id, ["char_id", "feat"])

        with conn.cursor() as cur:
            cur.executemany(
                """
                insert into {schema}.character_class (char_id, class, subclass, level)
                values (%s, %s, %s, %s);
                """
                .format(schema=schema),
                class_rows,
            )

            cur.executemany(
                """
                insert into {schema}.character_feats (char_id, feat)
                values (%s, %s);
                """
                .format(schema=schema),
                feat_rows,
            )

            conn.commit()

    return {
        "character": len(character_rows),
        "character_class": len(class_rows),
        "character_feats": len(feat_rows),
    }
