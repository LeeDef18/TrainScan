# TrainScan

TrainScan - сервис для автоматического определения ориентации железнодорожного вагона по изображению.

Сервис получает изображение вагона и тип вагона, запускает YOLO-модель детекции объектов, после чего применяет rule engine: найденные классы сверяются с таблицей правил ориентации из object storage. На выходе система возвращает итоговую метку:

- `A` - ориентация корректная
- `B` - ориентация некорректная

## Логика решения

Основной сценарий работы:

1. Пользователь отправляет изображение вагона и `wagon_type`.
2. Изображение проходит предварительную обработку.
3. YOLO-модель определяет ключевые объекты на изображении.
4. Результат инференса преобразуется в доменные сущности.
5. Rule engine получает список найденных объектов и тип вагона.
6. Сервис сверяет найденные объекты с таблицей правил из S3.
7. API возвращает детекции и итоговую оценку ориентации `A/B`.

Упрощенная схема:

```text
Image -> Preprocessing -> YOLO Inference -> Detection Mapping -> Rule Engine -> Orientation A/B
```

## Архитектура проекта

```text
app/
  application/      use case и прикладные порты
  core/             конфигурация приложения
  domain/           бизнес-сущности, доменные сервисы, интерфейсы репозиториев
  infrastructure/   адаптеры модели, S3, CSV, preprocessing, сериализация
  interfaces/       HTTP API
  main.py           точка входа FastAPI
tests/
  unit/             unit-тесты
.github/workflows/  CI/CD pipeline
docs/               проектная документация
```

Кратко по слоям:

- `app/domain` - бизнес-логика определения ориентации без привязки к FastAPI, S3 или YOLO
- `app/application` - orchestration сценария предсказания через `PredictUseCase`
- `app/infrastructure` - конкретные реализации для модели, rules table, preprocessing, S3 и сериализации
- `app/interfaces` - REST API слой
- `app/config/config.py` - единая точка доступа к переменным окружения

## Технологии

- Python 3.10
- FastAPI
- Ultralytics YOLO
- OpenCV
- NumPy
- Pillow
- Boto3
- Pytest
- Flake8, Pylint, Mypy, Black, isort
- GitHub Actions
- Docker

## Переменные окружения

Приложение использует настройки из `app/config/config.py`.

Основные переменные:

- `MODEL_PATH` - путь до локального файла модели после загрузки из object storage `model/best.pt`
- `MODEL_BUCKET` - bucket с моделью
- `MODEL_KEY` - ключ объекта модели в S3 `best.pt`
- `RULE_TABLE_BUCKET` - bucket с таблицей правил
- `RULE_TABLE_KEY` - ключ объекта CSV-таблицы правил в S3 `rule_table.csv`
- `S3_ENDPOINT` - endpoint S3-совместимого хранилища
- `S3_KEY` - access key
- `S3_SECRET` - secret key
- `MODEL_CONF` - confidence threshold для YOLO
- `MODEL_IOU` - IoU threshold для YOLO

Пример минимального заполнения `.env`:

```env
MODEL_PATH=model/best.pt
MODEL_BUCKET=wagon-models
MODEL_KEY=best.pt
RULE_TABLE_BUCKET=table-of-rule
RULE_TABLE_KEY=rule_table.csv
S3_ENDPOINT=https://s3.selcdn.ru
S3_KEY=<your-key>
S3_SECRET=<your-secret>
MODEL_CONF=0.25
MODEL_IOU=0.45
```

## Локальный запуск API

1. Создай и активируй виртуальное окружение.
```bash
python -m venv .venv
source .venv/bin/activate
```
2. Установи зависимости через `uv`.
```bash
uv sync --all-groups
```
3. Скопируй `.env.example` в `.env` и заполни параметры object storage.
4. Запусти FastAPI.
```bash
uvicorn app.main:app --reload
```

Для Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
uv sync --all-groups
uvicorn app.main:app --reload
```

После запуска API будет доступен по адресу:

```text
http://127.0.0.1:8000
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

## Воспроизведение результата через API

### Endpoint

- `POST /predict`

### Входные параметры

- `file` - изображение вагона
- `wagon_type` - тип вагона, для которого есть правило в таблице

При запуске сервис получает:

- модель из `MODEL_BUCKET` / `MODEL_KEY`
- таблицу правил из `RULE_TABLE_BUCKET` / `RULE_TABLE_KEY`

### Пример через curl

```bash
curl -X POST "http://127.0.0.1:8000/predict" \
  -F "file=@images/example.jpg" \
  -F "wagon_type=19-752"
```

### Пример ответа

```json
{
  "success": true,
  "predictions": [
    {
      "bbox": [100.1, 200.2, 300.3, 400.4],
      "bbox_int": [100, 200, 300, 400],
      "confidence": 0.95,
      "class": 0,
      "class_name": "valve"
    }
  ],
  "result_image": "<base64>",
  "original_image": "<base64>",
  "count": 1,
  "detected_classes": ["valve"],
  "wagon_type": "19-752",
  "orientation_check": "A"
}
```

## Тесты и качество кода

Запуск unit-тестов:

```bash
uv run pytest -q
```

Запуск тестов с покрытием:

```bash
uv run pytest --cov=app --cov-report=term-missing --cov-report=xml --cov-fail-under=70
```

Запуск проверок качества:

```bash
uv run black --check app tests
uv run isort --check-only app tests
uv run flake8 app tests
uv run pylint app --fail-under=8.0
uv run mypy app
```

В GitHub Actions после тестов сохраняется artifact `coverage-report` с файлом `coverage.xml`.

## Docker

Сборка образа:

```bash
docker build -t trainscan .
```

Запуск контейнера:

```bash
docker run --rm -p 8000:8000 \
  -e MODEL_PATH=model/best.pt \
  -e MODEL_BUCKET=wagon-models \
  -e MODEL_KEY=best.pt \
  -e RULE_TABLE_BUCKET=table-of-rule \
  -e RULE_TABLE_KEY=rule_table.csv \
  -e S3_ENDPOINT=https://s3.selcdn.ru \
  -e S3_KEY=<your-key> \
  -e S3_SECRET=<your-secret> \
  trainscan
```

## CI/CD

В репозитории настроен GitHub Actions pipeline:

- `lint` - black, isort, flake8, pylint, mypy
- `test` - unit-тесты и контроль покрытия не ниже 70%
- `docker` - проверка сборки Docker-образа

Coverage-отчет сохраняется как artifact после job `test`.

## Airflow DAG

В проект добавлен orchestration-слой `orchestration/airflow/`.

Что он показывает:

- использование `DockerOperator`
- вызов уже работающего TrainScan API
- идемпотентную запись результата по `execution_date`
- возможность backfill для нескольких дат
- отдельный runtime Airflow как внешнего orchestration-сервиса

Логика DAG:

1. Берет тестовое изображение из `orchestration/airflow/data/input/`
2. Запускает контейнер через `DockerOperator`
3. Контейнер вызывает `POST /predict`
4. Результат сохраняется в `orchestration/airflow/data/output/<ds>_prediction.json`

Идемпотентность:

- если файл результата для даты уже существует, повторный запуск не выполняет API-запрос повторно

Тестовый входной файл для DAG лежит в `orchestration/airflow/data/input/sample_wagon.jpg`.

Backfill пример:

```bash
airflow dags backfill wagon_orientation_pipeline --start-date 2026-04-01 --end-date 2026-04-03
```

Airflow запускается как отдельный сервис и не встраивается в `app/`, чтобы не смешивать orchestration и бизнес-логику.

## Dependency Management

Проект использует `uv` как основной менеджер зависимостей.

- runtime и dev-зависимости описаны в `pyproject.toml`
- lock-файл `uv.lock` фиксирует точные версии пакетов
- локальная установка выполняется через `uv sync`
- запуск команд внутри окружения выполняется через `uv run`
