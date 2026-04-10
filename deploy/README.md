# Deploy

Учебный production-like деплой строится так:

- Docker-образы публикуются в `GHCR`
- модель и таблица правил остаются в `Selectel S3`
- GitHub Actions после `push` в `main` подключается по `SSH` к VPS
- на VPS выполняется `docker compose pull && docker compose up -d`

## Что должно лежать на VPS

В каталоге `${SELECTEL_APP_DIR}` должны быть:

- `docker-compose.yml`
- `.env` (перезаписывается из GitHub Actions)

Минимальный bootstrap на VPS:

```bash
mkdir -p /opt/trainscan
```

Скопировать compose-файл можно один раз вручную:

```bash
scp deploy/docker-compose.yml <user>@<host>:/opt/trainscan/docker-compose.yml
```

## GitHub Secrets

- `SELECTEL_VPS_SSH_KEY`
- `S3_KEY`
- `S3_SECRET`

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

Рекомендуемое значение `SELECTEL_APP_DIR`: `/opt/trainscan`
