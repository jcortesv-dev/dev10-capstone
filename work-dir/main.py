from pathlib import Path
import dynaconf
from etl import ETLProcessor
from load import load_to_postgres


def _get_db_settings() -> dict[str, object] | None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    settings = dynaconf.Dynaconf(
        envvar_prefix=False,
        load_dotenv=True,
        dotenv_path=str(env_path),
        environments=False,
    )

    host = settings.get("DB_HOST")
    port = settings.get("DB_PORT", 5432)
    user = settings.get("DB_USER")
    password = settings.get("DB_PASSWORD")
    database = settings.get("DB_DATABASE")
    schema = settings.get("DB_SCHEMA", "characters")
    
    return {
        "host": host,
        "port": int(port),
        "user": user,
        "password": password,
        "dbname": database,
        "schema": schema,
    }


def main() -> None:
    processor = ETLProcessor()
    character_df, class_df, feat_df = processor.run()

    print(f"character rows: {len(character_df):,}")
    print(f"class rows: {len(class_df):,}")
    print(f"feat rows: {len(feat_df):,}")

    db_settings = _get_db_settings()

    connect_config = {
        "host": db_settings["host"],
        "port": db_settings["port"],
        "user": db_settings["user"],
        "password": db_settings["password"],
        "dbname": db_settings["dbname"],
    }

    loaded = load_to_postgres(
        character_df,
        class_df,
        feat_df,
        connect_config=connect_config,
        schema=db_settings["schema"],
    )
    print("\nloaded to postgres:")
    print(f"character rows inserted: {loaded['character']:,}")
    print(f"character_class rows inserted: {loaded['character_class']:,}")
    print(f"character_feats rows inserted: {loaded['character_feats']:,}")


if __name__ == "__main__":
    main()
