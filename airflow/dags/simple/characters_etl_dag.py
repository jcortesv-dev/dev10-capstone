import pendulum
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.sdk import dag, task


@dag(
    schedule=None,
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    tags=["capstone", "postgres"],
)
def characters_etl_dag():
    schema_task = SQLExecuteQueryOperator(
        task_id="create_schema",
        conn_id="pg_conn",
        sql="characters.sql",
    )

    @task()
    def etl():
        import sys
        from pathlib import Path

        project_root = Path("/opt/airflow/project")
        work_dir = project_root / "work-dir"
        sys.path.insert(0, str(work_dir))

        from etl import ETLProcessor
        from load import load_to_postgres

        processor = ETLProcessor(data_dir=str(project_root / "data"))
        character_df, class_df, feat_df = processor.run()

        hook = PostgresHook(postgres_conn_id="pg_conn")
        airflow_conn = hook.get_connection("pg_conn")

        connect_config = {
            "host": airflow_conn.host,
            "port": airflow_conn.port,
            "user": airflow_conn.login,
            "password": airflow_conn.password,
            "dbname": airflow_conn.schema,
        }

        load_to_postgres(
            character_df,
            class_df,
            feat_df,
            connect_config=connect_config,
            schema="characters",
        )

    schema_task >> etl()


characters_etl_dag()
