# TrainScan

TrainScan - сервис для автоматического определения ориентации железнодорожного вагона по изображению.

Сервис получает изображение вагона и тип вагона, запускает YOLO-модель детекции объектов, после чего применяет rule engine: найденные классы сверяются с таблицей правил ориентации. На выходе система возвращает итоговую метку:

- `A` - ориентация корректная
- `B` - ориентация некорректная

## Логика решения

Основной сценарий работы:

1. Пользователь отправляет изображение вагона и `wagon_type`.
2. Изображение проходит предварительную обработку.
3. YOLO-модель определяет ключевые объекты на изображении.
4. Результат инференса преобразуется в доменные сущности.
5. Rule engine получает список найденных объектов и тип вагона.
6. Сервис сверяет найденные объекты с таблицей правил.
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
- `app/infrastructure` - конкретные реализации для модели, CSV-таблицы, preprocessing, S3 и сериализации
- `app/interfaces` - REST API слой
- `app/core/config.py` - единая точка доступа к переменным окружения

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

Приложение использует настройки из `app/core/config.py`.

Основные переменные:

- `MODEL_PATH` - локальный путь до файла модели, по умолчанию `model/best.pt`
- `MODEL_KEY` - ключ объекта модели в S3, по умолчанию `best.pt`
- `S3_BUCKET` - bucket с моделью
- `S3_ENDPOINT` - endpoint S3-совместимого хранилища
- `S3_KEY` - access key
- `S3_SECRET` - secret key
- `RULE_TABLE` - путь до CSV-таблицы правил, по умолчанию `rule_table.csv`
- `MODEL_CONF` - confidence threshold для YOLO
- `MODEL_IOU` - IoU threshold для YOLO

Пример для PowerShell:

```powershell
$env:MODEL_PATH="model/best.pt"
$env:MODEL_KEY="best.pt"
$env:S3_BUCKET="wagon-models"
$env:S3_ENDPOINT="https://s3.selcdn.ru"
$env:S3_KEY="<your-key>"
$env:S3_SECRET="<your-secret>"
$env:RULE_TABLE="rule_table.csv"
$env:MODEL_CONF="0.25"
$env:MODEL_IOU="0.45"
```

## Локальный запуск API

1. Создай и активируй виртуальное окружение.
```bash
python -m venv .venv
source .venv/bin/activate
```
2. Установи зависимости.
```bash
pip install -r requirements.txt
```
3. Запусти FastAPI.
```bash
uvicorn app.main:app --reload
```

Для Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
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
pytest -q
```

Запуск тестов с покрытием:

```bash
pytest --cov=app --cov-report=term-missing --cov-report=xml --cov-fail-under=70
```

Запуск проверок качества:

```bash
black --check app tests
isort --check-only app tests
flake8 app tests
pylint app --fail-under=8.0
mypy app
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
  -e MODEL_KEY=best.pt \
  -e S3_BUCKET=wagon-models \
  -e S3_ENDPOINT=https://s3.selcdn.ru \
  -e S3_KEY=<your-key> \
  -e S3_SECRET=<your-secret> \
  -e RULE_TABLE=rule_table.csv \
  trainscan
```

## CI/CD

В репозитории настроен GitHub Actions pipeline:

- `lint` - black, isort, flake8, pylint, mypy
- `test` - unit-тесты и контроль покрытия не ниже 70%
- `docker` - проверка сборки Docker-образа

Coverage-отчет сохраняется как artifact после job `test`.
