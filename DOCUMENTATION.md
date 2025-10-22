# Meta Advanced Analytics Uploader - Документация

## Описание

Автоматизация получения данных из Meta Advanced Analytics API и загрузки их в Meta (раздел Uploaded) через официальный API.

## Возможности

- Получение списка тестов (ad_studies) с полной пагинацией
- Детальная информация о каждом тесте с кампаниями и целями
- Фильтрация по статусу кампаний (только ACTIVE)
- Фильтрация по дате окончания теста
- Нормализация целей Meta (Purchase / Initiate checkout)
- Автоматическое создание/обновление таблиц в Meta Advanced Analytics
- Загрузка данных через Upload Data API
- Предотвращение дубликатов с помощью audit log
- Различные режимы работы (dry-run, verify, smoke, force)

## Установка

1. Клонируйте репозиторий
2. Установите зависимости:

```bash
pip install -r requirements.txt
```

3. Создайте файл `.env` на основе `.env.example`:

```bash
cp .env.example .env
```

4. Заполните `.env` своими учетными данными:

```env
META_ACCESS_TOKEN=your_access_token_here
META_BUSINESS_ID=your_business_id_here
META_DATASET_ID=your_dataset_id_here
REFERENCE_CSV_PATH=reference.csv
```

## Получение учетных данных

### META_ACCESS_TOKEN

1. Перейдите в [Meta for Developers](https://developers.facebook.com/)
2. Создайте или выберите приложение
3. Перейдите в Tools > Access Token Tool
4. Сгенерируйте токен с правами:
   - `ads_read`
   - `business_management`

### META_BUSINESS_ID

1. Перейдите в [Business Manager](https://business.facebook.com/)
2. Settings > Business Settings
3. Скопируйте Business ID из URL или со страницы настроек

### META_DATASET_ID

1. Перейдите в Meta Advanced Analytics
2. Откройте нужный датасет
3. ID датасета находится в URL: `https://www.facebook.com/analytics/<DATASET_ID>/...`

## Использование

### Базовая команда

```bash
python meta_analytics_uploader.py
```

### Режимы работы

#### 1. Dry-run (тестовый запуск без загрузки)

```bash
python meta_analytics_uploader.py --dry-run
```

Показывает:
- Схему таблицы
- Количество строк для загрузки
- Статистику по тестам

#### 2. Smoke тест (загрузка первых N строк)

```bash
python meta_analytics_uploader.py --smoke 10
```

Загружает только первые 10 строк для проверки.

#### 3. Verify (проверка после загрузки)

```bash
python meta_analytics_uploader.py --verify
```

После загрузки выполняет запрос к таблице для проверки наличия данных.

#### 4. Force (перезагрузка уже загруженных тестов)

```bash
python meta_analytics_uploader.py --force
```

Игнорирует audit log и загружает все тесты заново.

#### 5. Комбинированные режимы

```bash
python meta_analytics_uploader.py --smoke 5 --verify --dry-run
python meta_analytics_uploader.py --force --verify
```

### Дополнительные параметры

#### Фильтрация по дате

```bash
python meta_analytics_uploader.py --days 30
```

Исключает тесты, которые закончились более 30 дней назад (по умолчанию: 14 дней).

#### Название таблицы

```bash
python meta_analytics_uploader.py --table-name my_custom_table
```

По умолчанию используется `uploaded_ad_studies`.

## Структура данных

### Эталонная схема CSV

Файл `reference.csv` определяет структуру выходных данных:

```csv
campaign_id,study_id,objective_purchase_id,objective_session_id,ds
6795773503955,4287253134828020,782050654580798,773342022531899,2025-10-15
...
```

**Колонки:**

| Название | Тип | Описание |
|----------|-----|----------|
| `campaign_id` | string | ID кампании из Meta Ads |
| `study_id` | string | ID теста (ad_study) |
| `objective_purchase_id` | string | ID цели "Purchase" (может быть пустым) |
| `objective_session_id` | string | ID цели "Initiate checkout" (может быть пустым) |
| `ds` | date | Дата загрузки (YYYY-MM-DD) |

### Типы данных Meta Advanced Analytics

Скрипт автоматически преобразует типы Python в типы Meta:

- `string` - строковые данные
- `integer` - целые числа
- `double` - числа с плавающей точкой
- `date` - даты (YYYY-MM-DD)
- `timestamp` - дата и время

## Логика работы

### 1. Получение списка тестов

```
GET /<BUSINESS_ID>/ad_studies?fields=id,name,type,description,start_time,end_time&limit=100
```

- Реализована полная пагинация через `paging.next`
- Получаем только `study_id` для дальнейшей обработки

### 2. Получение деталей теста

```
GET /<STUDY_ID>?fields=id,name,type,start_time,end_time,cells{...},objectives{...}
```

Получаем:
- Информацию о кампаниях и их статусах
- Цели (objectives) теста
- Настройки ячеек (cells)

### 3. Фильтрация

**По дате:**
- Исключаем тесты, где `end_time < now() - X days` (X = 14 по умолчанию)

**По статусу кампаний:**
- Включаем тест, если хотя бы одна кампания `status = "ACTIVE"`
- Игнорируем кампании с статусами: `PAUSED`, `ARCHIVED`, `DELETED`

### 4. Нормализация целей

Meta возвращает различные варианты названий целей. Скрипт нормализует их к двум категориям:

**Purchase:**
- Ключевые слова: `purchase`, `buy`, `fb_mobile_purchase`, `mobile_purchase`
- Нормализованное имя: `Purchase`
- Поле: `objective_purchase_id`

**Initiate checkout:**
- Ключевые слова: `checkout`, `initiated_checkout`, `fb_mobile_initiated_checkout`
- Нормализованное имя: `Initiate checkout`
- Поле: `objective_session_id`

Остальные цели (activate, install и т.п.) **игнорируются**.

### 5. Удаление дубликатов

Скрипт автоматически удаляет дубликаты по паре `(study_id, campaign_id)`.

### 6. Audit Log

Для предотвращения повторных загрузок ведется лог в файле `upload_audit_log.jsonl`:

```json
{"study_id": "123", "ds": "2025-10-15", "upload_session_id": "2025-10-15T10:30:00", "status": "success", "details": "Uploaded 10 rows"}
```

## API документация Meta

- [General Documentation](https://developers.facebook.com/docs/advanced-analytics-api)
- [Create Table API](https://developers.facebook.com/docs/advanced-analytics-api/create-table)
- [Upload Data API](https://developers.facebook.com/docs/advanced-analytics-api/upload-data)

## Логирование

Скрипт ведет логи в двух местах:

1. **Консоль** - вывод в STDOUT
2. **Файл** - `meta_uploader.log`

Уровни логирования:
- `INFO` - основная информация о процессе
- `WARNING` - предупреждения (например, о дубликатах)
- `ERROR` - ошибки выполнения
- `DEBUG` - детальная информация (по умолчанию отключено)

### Включение DEBUG режима

Измените в скрипте:

```python
logging.basicConfig(
    level=logging.DEBUG,  # было: logging.INFO
    ...
)
```

## Обработка ошибок

### API ошибки

Скрипт использует retry-стратегию для HTTP запросов:
- 3 попытки
- Экспоненциальная задержка (1s, 2s, 4s)
- Retry для статусов: 429, 500, 502, 503, 504

### Частые ошибки

**1. Invalid Access Token**

```
Ошибка: META_ACCESS_TOKEN не установлен или недействителен
```

Решение: Проверьте токен и его права доступа.

**2. Business ID not found**

```
Ошибка: META_BUSINESS_ID не найден
```

Решение: Проверьте правильность Business ID.

**3. Dataset not accessible**

```
Ошибка: META_DATASET_ID недоступен
```

Решение: Убедитесь, что токен имеет доступ к датасету.

**4. Schema mismatch**

```
Ошибка: Данные не соответствуют схеме эталона
```

Решение: Проверьте `reference.csv` и убедитесь, что колонки совпадают.

## Примеры использования

### Полный цикл загрузки

```bash
# 1. Проверка данных (dry-run)
python meta_analytics_uploader.py --dry-run

# 2. Тестовая загрузка 5 строк
python meta_analytics_uploader.py --smoke 5 --verify

# 3. Полная загрузка с проверкой
python meta_analytics_uploader.py --verify

# 4. Проверка логов
cat upload_audit_log.jsonl
```

### Периодическая загрузка (cron)

Добавьте в crontab:

```bash
# Ежедневная загрузка в 3:00 AM
0 3 * * * cd /path/to/project && /usr/bin/python3 meta_analytics_uploader.py >> /var/log/meta_upload.log 2>&1
```

### Использование с виртуальным окружением

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python meta_analytics_uploader.py
```

## Критерии приёмки

- [x] Таблица создана или проверена через Create Table API
- [x] Загружены только новые тесты (без повторов)
- [x] Нормализация целей корректна для всех известных вариантов Meta
- [x] Структура выгрузки полностью совпадает с эталоном
- [x] Загрузка через Upload Data API
- [x] Все проверки (--dry-run, --verify) работают

## Дальнейшее развитие

### Планируемые функции

1. **Auto-evolve режим** (`--auto-evolve`)
   - Автоматическое обновление схемы при изменении эталона

2. **Параллельная обработка**
   - Ускорение получения деталей тестов через многопоточность

3. **Webhook уведомления**
   - Отправка уведомлений о результатах загрузки

4. **Инкрементальная загрузка**
   - Загрузка только новых данных с момента последнего запуска

5. **Dashboard**
   - Web-интерфейс для мониторинга загрузок

## Поддержка

Если у вас возникли проблемы:

1. Проверьте логи в `meta_uploader.log`
2. Запустите в режиме `--dry-run` для диагностики
3. Проверьте audit log: `upload_audit_log.jsonl`
4. Убедитесь, что все переменные окружения установлены корректно

## Лицензия

MIT License

## Автор

Sergei Melchugov
- Telegram: [@melcepera](https://t.me/melcepera)
- LinkedIn: [melchugov](https://www.linkedin.com/in/melchugov)
