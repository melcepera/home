# Meta Advanced Analytics Uploader

Автоматизация получения данных из Meta Advanced Analytics API и загрузки их в Meta (раздел Uploaded).

## Быстрый старт

### 1. Установка

```bash
pip install -r requirements.txt
```

### 2. Конфигурация

Создайте файл `.env`:

```bash
cp .env.example .env
```

Заполните переменные окружения:

```env
META_ACCESS_TOKEN=your_token
META_BUSINESS_ID=your_business_id
META_DATASET_ID=your_dataset_id
REFERENCE_CSV_PATH=reference.csv
```

### 3. Запуск

```bash
# Тестовый запуск (без загрузки)
python meta_analytics_uploader.py --dry-run

# Реальная загрузка с проверкой
python meta_analytics_uploader.py --verify
```

## Возможности

- Автоматическое получение тестов (ad_studies) из Meta API с пагинацией
- Фильтрация по статусу кампаний (только ACTIVE)
- Нормализация целей (Purchase / Initiate checkout)
- Предотвращение дубликатов через audit log
- Различные режимы: dry-run, verify, smoke, force

## Режимы работы

| Флаг | Описание |
|------|----------|
| `--dry-run` | Проверка без загрузки |
| `--verify` | Проверка после загрузки |
| `--smoke N` | Загрузка первых N строк |
| `--force` | Перезагрузка всех тестов |
| `--days N` | Фильтр по дате (default: 14) |
| `--table-name` | Название таблицы (default: uploaded_ad_studies) |

## Структура данных

Эталонная схема определена в `reference.csv`:

```csv
campaign_id,study_id,objective_purchase_id,objective_session_id,ds
6795773503955,4287253134828020,782050654580798,773342022531899,2025-10-15
```

## Документация

Полная документация: [DOCUMENTATION.md](./DOCUMENTATION.md)

## API Endpoints

Скрипт использует официальные Meta Advanced Analytics API:

- [Create Table API](https://developers.facebook.com/docs/advanced-analytics-api/create-table)
- [Upload Data API](https://developers.facebook.com/docs/advanced-analytics-api/upload-data)

## Примеры

```bash
# Тестовая загрузка 5 строк с проверкой
python meta_analytics_uploader.py --smoke 5 --verify

# Загрузка с фильтром 30 дней
python meta_analytics_uploader.py --days 30 --verify

# Принудительная перезагрузка всех тестов
python meta_analytics_uploader.py --force
```

## Логирование

- **Консоль**: вывод в реальном времени
- **Файл**: `meta_uploader.log`
- **Audit log**: `upload_audit_log.jsonl`

## Фильтры

### По дате
Исключаются тесты где `end_time < now() - X days`

### По статусу
- Включаются: кампании со статусом `ACTIVE`
- Игнорируются: `PAUSED`, `ARCHIVED`, `DELETED`

### По целям
- **Purchase**: purchase, buy, fb_mobile_purchase
- **Checkout**: checkout, initiated_checkout

## Структура проекта

```
.
├── meta_analytics_uploader.py  # Основной скрипт
├── reference.csv               # Эталонная схема данных
├── requirements.txt            # Зависимости
├── .env.example               # Пример конфигурации
├── .gitignore                 # Игнорируемые файлы
├── DOCUMENTATION.md           # Полная документация
└── PROJECT_README.md          # Этот файл
```

## Troubleshooting

### Ошибка: Invalid Access Token

Проверьте права доступа токена:
- `ads_read`
- `business_management`

### Ошибка: Dataset not accessible

Убедитесь, что токен имеет доступ к указанному датасету.

### Ошибка: Schema mismatch

Проверьте соответствие `reference.csv` ожидаемой схеме.

## Поддержка

Вопросы и проблемы: [GitHub Issues](https://github.com/melcepera/home/issues)

## Автор

**Sergei Melchugov**
- Telegram: [@melcepera](https://t.me/melcepera)
- LinkedIn: [melchugov](https://www.linkedin.com/in/melchugov)

## Лицензия

MIT License
