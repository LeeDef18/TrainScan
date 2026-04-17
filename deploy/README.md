# Deploy

production-like деплой строится так:

- Docker-образы публикуются в `GHCR`
- модель и таблица правил остаются в `Selectel S3`
- GitHub Actions после `push` в `main` подключается по `SSH` к VPS
- на VPS выполняется `docker compose pull && docker compose up -d`
- внешний трафик идет через `Nginx` на `80` порт, а FastAPI и Airflow Webserver остаются внутренними сервисами внутри compose-сети

## Что должно лежать на VPS

В каталоге `${SELECTEL_APP_DIR}` должны быть:

- `docker-compose.yml`
- `.env` (перезаписывается из GitHub Actions)
- `nginx/default.conf`

Минимальный bootstrap на VPS:

```bash
mkdir -p /opt/trainscan
```

Скопировать compose-файл можно один раз вручную:

```bash
scp deploy/docker-compose.yml <user>@<host>:/opt/trainscan/docker-compose.yml
```

И конфиг Nginx:

```bash
scp -r deploy/nginx <user>@<host>:/opt/trainscan/
```

Текущий workflow также сам обновляет `docker-compose.yml`, `nginx/default.conf` и копирует дерево проекта в `${SELECTEL_APP_DIR}/project` на VPS.
Также он создает общую Docker-сеть `trainscan-shared`, чтобы `Nginx`, API и Airflow видели друг друга по service name.

## GitHub Secrets

- `SELECTEL_VPS_SSH_KEY`
- `S3_KEY`
- `S3_SECRET`
- `AIRFLOW_DB_PASSWORD`
- `AIRFLOW_ADMIN_PASSWORD`

## GitHub Variables

- `SELECTEL_VPS_HOST`
- `SELECTEL_VPS_USER`
- `SELECTEL_VPS_SSH_PORT`
- `SELECTEL_APP_DIR`
- `APP_PORT`
- `LOG_LEVEL`
- `MODEL_PATH`
- `MODEL_BUCKET`
- `MODEL_KEY`
- `RULE_TABLE_PATH`
- `RULE_TABLE_BUCKET`
- `RULE_TABLE_KEY`
- `S3_ENDPOINT`
- `MODEL_CONF`
- `MODEL_IOU`
- `AIRFLOW_BASE_URL`
- `TRAINSCAN_API_URL`
- `AIRFLOW_S3_LOG_BUCKET`
- `AIRFLOW_S3_LOG_PREFIX`
- `AIRFLOW_OUTPUT_BUCKET`
- `AIRFLOW_ADMIN_USERNAME`
- `AIRFLOW_ADMIN_EMAIL`

Рекомендуемое значение `SELECTEL_APP_DIR`: `/opt/trainscan`

## Airflow на VPS

Airflow деплоится отдельным compose-файлом в `${SELECTEL_APP_DIR}/airflow/docker-compose.yml`, но наружу напрямую не публикуется на своем внутреннем порту `8080`.
Доступ к Airflow UI идет через общий `Nginx` reverse proxy в сети `trainscan-shared`, но на отдельном внешнем порту `81`.

Текущая схема маршрутизации без доменов:

```text
http://<server-ip>/        -> TrainScan API
http://<server-ip>/docs    -> Swagger UI
http://<server-ip>:81/     -> Airflow Webserver
```

Внешний порт `8080` для Airflow больше не нужен. Если он открыт в security group, его можно закрыть.
Для доступа к Airflow нужно открыть внешний порт `81`.

Логи Airflow task-ов отправляются в Selectel S3 через тот же аккаунт Object Storage.
Постоянный named volume для task logs больше не используется: source of truth для логов - S3 и UI Airflow.
Для этого используются:

- `S3_ENDPOINT`
- `S3_KEY`
- `S3_SECRET`
- `AIRFLOW_S3_LOG_BUCKET`
- `AIRFLOW_S3_LOG_PREFIX`

Результат task `predict_orientation` также сохраняется в S3 и перезаписывается по ключу вида:

```text
<YYYY-MM-DD>_prediction.json
```

Для него используется bucket `AIRFLOW_OUTPUT_BUCKET`.
