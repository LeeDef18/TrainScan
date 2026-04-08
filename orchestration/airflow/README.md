# Airflow Orchestration

Airflow вынесен в отдельный orchestration-слой и не содержит бизнес-логику определения ориентации.

## Почему это не нарушает Clean Architecture

- `app/` остается ядром системы и содержит бизнес-логику
- `orchestration/airflow/` только оркестрирует вызов уже существующего сервиса
- DAG не дублирует ML-логику, rule engine или preprocessing
- Airflow выступает как внешний delivery/orchestration слой

## Что делает DAG

- использует `DockerOperator`
- запускает временный контейнер
- отправляет тестовое изображение в `POST /predict`
- записывает результат в `orchestration/airflow/data/output/<ds>_prediction.json`

## Идемпотентность

- путь результата зависит от `execution_date`
- если файл результата уже существует, повторный запуск на ту же дату завершается без повторного запроса в API

## Backfill

DAG по умолчанию не запускается по расписанию автоматически: `schedule=None`, `catchup=False`.

Это сделано специально, чтобы он не создавал бесконечные daily runs в локальном стенде.

Backfill при этом все равно можно продемонстрировать вручную:

```bash
airflow dags backfill wagon_orientation_pipeline --start-date 2026-04-01 --end-date 2026-04-03
```

Для каждой даты будет создан отдельный output-файл.

## Запуск как отдельного сервиса

Да, Airflow в этом проекте должен быть отдельным сервисом.

Причины:

- у него свой runtime и жизненный цикл
- ему нужны scheduler, webserver и metadata database
- он не должен встраиваться в `app/` как часть бизнес-ядра

Локальный запуск:

1. Поднять TrainScan API отдельно.
2. Перейти в `orchestration/airflow/config`.
3. Выполнить:

```bash
docker compose down -v
docker compose up airflow-init
docker compose up -d airflow-webserver airflow-scheduler
```

После этого UI Airflow будет доступен на `http://127.0.0.1:8080`.

Учетные данные администратора Airflow больше не захардкожены в compose-файле и читаются из `.env`:

- `AIRFLOW_ADMIN_USERNAME`
- `AIRFLOW_ADMIN_PASSWORD`
- `AIRFLOW_ADMIN_EMAIL`

Если в UI не открываются логи, можно посмотреть их напрямую:

```bash
docker compose logs airflow-scheduler
docker compose logs airflow-webserver
```
