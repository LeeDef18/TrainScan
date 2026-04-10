from __future__ import annotations

import os
from datetime import datetime

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.providers.docker.operators.docker import DockerOperator
from docker.types import Mount

API_URL = os.getenv("TRAINSCAN_API_URL", "http://nginx")
PROJECT_ROOT = "/opt/project"
INPUT_IMAGE = "/opt/project/orchestration/airflow/data/input/sample_wagon.jpg"
OUTPUT_KEY = "{{ ds }}_prediction.json"
REQUEST_IMAGE = "ghcr.io/astral-sh/uv:0.6.14-python3.11-bookworm-slim"

with DAG(
    dag_id="wagon_orientation_pipeline",
    description="Idempotent wagon orientation pipeline over TrainScan API.",
    start_date=datetime(2026, 4, 1),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=["trainscan", "airflow", "docker"],
) as dag:
    start = EmptyOperator(task_id="start")

    predict_orientation = DockerOperator(
        task_id="predict_orientation",
        image=REQUEST_IMAGE,
        api_version="auto",
        auto_remove="success",
        command=(
            'sh -c "uv run --with requests '
            "python /opt/project/orchestration/airflow/scripts/request_prediction.py "
            f'{API_URL} {INPUT_IMAGE} 19-752 {OUTPUT_KEY}"'
        ),
        docker_url="unix://var/run/docker.sock",
        network_mode="trainscan-shared",
        mount_tmp_dir=False,
        mounts=[
            Mount(
                source="/opt/trainscan/project",
                target="/opt/project",
                type="bind",
            )
        ],
        working_dir=PROJECT_ROOT,
        retrieve_output=False,
    )

    finish = EmptyOperator(task_id="finish")

    start >> predict_orientation >> finish
