#!/usr/bin/env python3
"""
Meta Advanced Analytics Uploader
Автоматизация загрузки данных из Meta Advanced Analytics API в Meta Uploaded таблицы
"""

import argparse
import csv
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('meta_uploader.log')
    ]
)
logger = logging.getLogger(__name__)


class Config:
    """Конфигурация приложения"""

    def __init__(self):
        self.access_token = os.getenv('META_ACCESS_TOKEN')
        self.business_id = os.getenv('META_BUSINESS_ID')
        self.dataset_id = os.getenv('META_DATASET_ID')
        self.reference_csv_path = os.getenv('REFERENCE_CSV_PATH', 'reference.csv')
        self.base_url = 'https://graph.facebook.com/v21.0/'
        self.audit_log_path = 'upload_audit_log.jsonl'

        self._validate()

    def _validate(self):
        """Проверка наличия обязательных параметров"""
        if not self.access_token:
            raise ValueError("META_ACCESS_TOKEN не установлен")
        if not self.business_id:
            raise ValueError("META_BUSINESS_ID не установлен")
        if not self.dataset_id:
            raise ValueError("META_DATASET_ID не установлен")


class MetaAPIClient:
    """Клиент для работы с Meta Advanced Analytics API"""

    def __init__(self, config: Config):
        self.config = config
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Создание сессии с retry стратегией"""
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None,
                     data: Optional[Dict] = None, files: Optional[Dict] = None) -> Dict:
        """Выполнение HTTP запроса к API"""
        url = urljoin(self.config.base_url, endpoint)

        if params is None:
            params = {}
        params['access_token'] = self.config.access_token

        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=params, timeout=30)
            elif method.upper() == 'POST':
                if files:
                    response = self.session.post(url, params=params, files=files, timeout=120)
                else:
                    response = self.session.post(url, params=params, json=data, timeout=60)
            else:
                raise ValueError(f"Неподдерживаемый HTTP метод: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка API запроса: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Ответ сервера: {e.response.text}")
            raise

    def get_ad_studies(self, limit: int = 100) -> List[Dict]:
        """
        Получение списка всех тестов с пагинацией
        GET /<BUSINESS_ID>/ad_studies?fields=id,name,type,description,start_time,end_time&limit=100
        """
        logger.info("Получение списка тестов...")
        all_studies = []
        endpoint = f"{self.config.business_id}/ad_studies"
        params = {
            'fields': 'id,name,type,description,start_time,end_time',
            'limit': limit
        }

        while True:
            response = self._make_request('GET', endpoint, params=params)
            studies = response.get('data', [])
            all_studies.extend(studies)

            logger.info(f"Получено тестов: {len(studies)}, всего: {len(all_studies)}")

            # Пагинация
            paging = response.get('paging', {})
            next_url = paging.get('next')

            if not next_url:
                break

            # Извлекаем параметры из next URL
            if 'after' in next_url:
                import re
                after_match = re.search(r'after=([^&]+)', next_url)
                if after_match:
                    params['after'] = after_match.group(1)
            else:
                break

        logger.info(f"Всего получено тестов: {len(all_studies)}")
        return all_studies

    def get_study_details(self, study_id: str) -> Dict:
        """
        Получение детальной информации о тесте
        GET /<STUDY_ID>?fields=id,name,type,start_time,end_time,cells{...},objectives{...}
        """
        logger.debug(f"Получение деталей теста {study_id}")

        fields = (
            'id,name,type,start_time,end_time,'
            'cells{name,id,treatment_percentage,campaigns{id,name,objective,account_id,status}},'
            'objectives{id,name,type,applications{data{name,namespace,event_names,id}}}'
        )

        params = {'fields': fields}
        response = self._make_request('GET', study_id, params=params)
        return response

    def create_or_update_table(self, table_name: str, schema: List[Dict]) -> Dict:
        """
        Создание или обновление таблицы через Create Table API
        POST /<DATASET_ID>/create_table
        """
        logger.info(f"Создание/обновление таблицы: {table_name}")

        endpoint = f"{self.config.dataset_id}/create_table"
        data = {
            'name': table_name,
            'columns': schema
        }

        try:
            response = self._make_request('POST', endpoint, data=data)
            logger.info(f"Таблица создана/обновлена: {response}")
            return response
        except Exception as e:
            logger.warning(f"Ошибка создания таблицы (возможно, уже существует): {e}")
            return {}

    def upload_data(self, table_name: str, csv_file_path: str) -> Dict:
        """
        Загрузка данных через Upload Data API
        POST /<DATASET_ID>/upload_data
        """
        logger.info(f"Загрузка данных из {csv_file_path} в таблицу {table_name}")

        endpoint = f"{self.config.dataset_id}/upload_data"

        with open(csv_file_path, 'rb') as f:
            files = {
                'file': (os.path.basename(csv_file_path), f, 'text/csv')
            }
            params = {
                'table_name': table_name,
                'access_token': self.config.access_token
            }

            url = urljoin(self.config.base_url, endpoint)
            response = self.session.post(url, params=params, files=files, timeout=300)
            response.raise_for_status()
            result = response.json()

        logger.info(f"Результат загрузки: {result}")
        return result

    def query_table(self, query: str) -> List[Dict]:
        """
        Выполнение запроса к таблице для проверки данных
        POST /<DATASET_ID>/query
        """
        endpoint = f"{self.config.dataset_id}/query"
        data = {'query': query}

        try:
            response = self._make_request('POST', endpoint, data=data)
            return response.get('data', [])
        except Exception as e:
            logger.error(f"Ошибка выполнения запроса: {e}")
            return []


class SchemaManager:
    """Управление схемой данных на основе эталонного CSV"""

    # Маппинг типов Python -> Meta Advanced Analytics
    TYPE_MAPPING = {
        'int': 'integer',
        'float': 'double',
        'str': 'string',
        'date': 'date',
        'datetime': 'timestamp'
    }

    def __init__(self, reference_csv_path: str):
        self.reference_csv_path = reference_csv_path
        self.columns = []
        self.column_order = []
        self._load_schema()

    def _load_schema(self):
        """Загрузка схемы из эталонного CSV"""
        if not os.path.exists(self.reference_csv_path):
            logger.warning(f"Эталонный CSV не найден: {self.reference_csv_path}")
            # Используем хардкодированную схему как fallback
            self._use_default_schema()
            return

        with open(self.reference_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            self.column_order = reader.fieldnames

            # Определяем типы данных из первой строки
            first_row = next(reader, None)
            if first_row:
                self.columns = self._infer_types(first_row)
            else:
                self._use_default_schema()

        logger.info(f"Схема загружена из {self.reference_csv_path}: {self.column_order}")

    def _use_default_schema(self):
        """Использование схемы по умолчанию"""
        self.column_order = [
            'campaign_id',
            'study_id',
            'objective_purchase_id',
            'objective_session_id',
            'ds'
        ]
        self.columns = [
            {'name': 'campaign_id', 'type': 'string'},
            {'name': 'study_id', 'type': 'string'},
            {'name': 'objective_purchase_id', 'type': 'string'},
            {'name': 'objective_session_id', 'type': 'string'},
            {'name': 'ds', 'type': 'date'}
        ]
        logger.info("Используется схема по умолчанию")

    def _infer_types(self, sample_row: Dict) -> List[Dict]:
        """Определение типов данных из примера"""
        columns = []

        for col_name in self.column_order:
            value = sample_row.get(col_name, '')

            # Определяем тип
            if col_name == 'ds' or 'date' in col_name.lower():
                col_type = 'date'
            elif col_name.endswith('_id'):
                col_type = 'string'  # ID храним как строки (могут быть большими)
            elif value and value.replace('.', '').replace('-', '').isdigit():
                col_type = 'double' if '.' in value else 'integer'
            else:
                col_type = 'string'

            columns.append({
                'name': col_name,
                'type': col_type
            })

        return columns

    def get_schema(self) -> List[Dict]:
        """Получение схемы для Create Table API"""
        return self.columns

    def validate_data(self, data: List[Dict]) -> bool:
        """Проверка данных на соответствие схеме"""
        if not data:
            return True

        first_row = data[0]
        missing_cols = set(self.column_order) - set(first_row.keys())

        if missing_cols:
            logger.error(f"Отсутствуют колонки: {missing_cols}")
            return False

        extra_cols = set(first_row.keys()) - set(self.column_order)
        if extra_cols:
            logger.warning(f"Дополнительные колонки будут удалены: {extra_cols}")

        return True

    def normalize_data(self, data: List[Dict]) -> List[Dict]:
        """Приведение данных к схеме эталона"""
        normalized = []

        for row in data:
            normalized_row = {}
            for col in self.column_order:
                value = row.get(col, '')

                # Обработка пустых значений
                if value is None or value == '':
                    normalized_row[col] = ''
                else:
                    normalized_row[col] = str(value)

            normalized.append(normalized_row)

        return normalized


class ObjectiveNormalizer:
    """Нормализация целей Meta"""

    PURCHASE_KEYWORDS = ['purchase', 'buy', 'fb_mobile_purchase', 'mobile_purchase']
    CHECKOUT_KEYWORDS = ['checkout', 'initiated_checkout', 'fb_mobile_initiated_checkout']

    @staticmethod
    def normalize_objective_name(raw_name: str) -> Optional[str]:
        """
        Нормализация названия цели
        Возвращает: 'Purchase' | 'Initiate checkout' | None
        """
        if not raw_name:
            return None

        name_lower = raw_name.lower()

        if any(keyword in name_lower for keyword in ObjectiveNormalizer.PURCHASE_KEYWORDS):
            return 'Purchase'
        elif any(keyword in name_lower for keyword in ObjectiveNormalizer.CHECKOUT_KEYWORDS):
            return 'Initiate checkout'

        return None

    @staticmethod
    def extract_objectives(study_details: Dict) -> Dict[str, str]:
        """
        Извлечение и нормализация целей из ответа API
        Возвращает: {'purchase_id': '...', 'session_id': '...'}
        """
        objectives_data = study_details.get('objectives', {}).get('data', [])
        result = {
            'purchase_id': None,
            'session_id': None
        }

        for obj in objectives_data:
            obj_name = obj.get('name', '')
            obj_id = obj.get('id', '')

            normalized_name = ObjectiveNormalizer.normalize_objective_name(obj_name)

            if normalized_name == 'Purchase':
                result['purchase_id'] = obj_id
            elif normalized_name == 'Initiate checkout':
                result['session_id'] = obj_id

        return result


class AuditLogger:
    """Логирование загрузок для предотвращения дубликатов"""

    def __init__(self, log_path: str):
        self.log_path = log_path
        self.uploaded_studies = self._load_uploaded_studies()

    def _load_uploaded_studies(self) -> set:
        """Загрузка списка уже загруженных study_id"""
        if not os.path.exists(self.log_path):
            return set()

        studies = set()
        with open(self.log_path, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get('status') == 'success':
                        studies.add(entry.get('study_id'))
                except json.JSONDecodeError:
                    continue

        logger.info(f"Загружено {len(studies)} уже загруженных тестов из audit log")
        return studies

    def is_uploaded(self, study_id: str) -> bool:
        """Проверка, был ли тест уже загружен"""
        return study_id in self.uploaded_studies

    def log_upload(self, study_id: str, ds: str, status: str, details: str = ''):
        """Запись в audit log"""
        entry = {
            'study_id': study_id,
            'ds': ds,
            'upload_session_id': datetime.now().isoformat(),
            'status': status,
            'details': details
        }

        with open(self.log_path, 'a') as f:
            f.write(json.dumps(entry) + '\n')

        if status == 'success':
            self.uploaded_studies.add(study_id)


class DataProcessor:
    """Основная логика обработки и загрузки данных"""

    def __init__(self, config: Config, args: argparse.Namespace):
        self.config = config
        self.args = args
        self.api_client = MetaAPIClient(config)
        self.schema_manager = SchemaManager(config.reference_csv_path)
        self.audit_logger = AuditLogger(config.audit_log_path)

    def filter_studies(self, studies: List[Dict]) -> List[str]:
        """
        Фильтрация тестов по дате окончания
        Исключаем тесты, где end_time < now() - X days
        """
        cutoff_date = datetime.now() - timedelta(days=self.args.days)
        filtered_ids = []

        for study in studies:
            study_id = study.get('id')
            end_time_str = study.get('end_time')

            if not end_time_str:
                # Если нет end_time, включаем тест
                filtered_ids.append(study_id)
                continue

            try:
                # Формат: "2025-10-15T00:00:00+0000"
                end_time = datetime.fromisoformat(end_time_str.replace('+0000', ''))

                if end_time >= cutoff_date:
                    filtered_ids.append(study_id)
                else:
                    logger.debug(f"Тест {study_id} исключен: end_time {end_time} < cutoff {cutoff_date}")
            except ValueError as e:
                logger.warning(f"Ошибка парсинга даты для теста {study_id}: {e}")
                filtered_ids.append(study_id)  # На всякий случай включаем

        logger.info(f"После фильтрации по дате осталось тестов: {len(filtered_ids)}")
        return filtered_ids

    def has_active_campaigns(self, study_details: Dict) -> bool:
        """
        Проверка наличия активных кампаний
        Включаем тест только если хотя бы одна кампания ACTIVE
        """
        cells = study_details.get('cells', {}).get('data', [])

        for cell in cells:
            campaigns = cell.get('campaigns', {}).get('data', [])
            for campaign in campaigns:
                if campaign.get('status') == 'ACTIVE':
                    return True

        return False

    def extract_data_from_study(self, study_details: Dict) -> List[Dict]:
        """
        Извлечение данных из детальной информации о тесте
        Создает строки в формате эталонного CSV
        """
        study_id = study_details.get('id')
        cells = study_details.get('cells', {}).get('data', [])

        # Извлекаем нормализованные цели
        objectives = ObjectiveNormalizer.extract_objectives(study_details)
        objective_purchase_id = objectives['purchase_id'] or ''
        objective_session_id = objectives['session_id'] or ''

        # Текущая дата для ds
        ds = datetime.now().strftime('%Y-%m-%d')

        rows = []

        for cell in cells:
            campaigns = cell.get('campaigns', {}).get('data', [])

            for campaign in campaigns:
                campaign_status = campaign.get('status')

                # Игнорируем неактивные кампании
                if campaign_status in ['PAUSED', 'ARCHIVED', 'DELETED']:
                    continue

                campaign_id = campaign.get('id')

                row = {
                    'campaign_id': campaign_id,
                    'study_id': study_id,
                    'objective_purchase_id': objective_purchase_id,
                    'objective_session_id': objective_session_id,
                    'ds': ds
                }

                rows.append(row)

        return rows

    def process_all_studies(self) -> List[Dict]:
        """Обработка всех тестов и сборка данных"""
        logger.info("Начало обработки тестов...")

        # Шаг 1: Получение списка тестов
        all_studies = self.api_client.get_ad_studies()

        # Шаг 2: Фильтрация по дате
        filtered_study_ids = self.filter_studies(all_studies)

        # Шаг 3: Обработка каждого теста
        all_rows = []
        processed_count = 0
        skipped_count = 0

        for study_id in filtered_study_ids:
            # Проверка на дубликат
            if not self.args.force and self.audit_logger.is_uploaded(study_id):
                logger.debug(f"Тест {study_id} уже загружен, пропускаем")
                skipped_count += 1
                continue

            try:
                # Получение деталей
                study_details = self.api_client.get_study_details(study_id)

                # Фильтрация по активным кампаниям
                if not self.has_active_campaigns(study_details):
                    logger.debug(f"Тест {study_id} не имеет активных кампаний, пропускаем")
                    skipped_count += 1
                    continue

                # Извлечение данных
                rows = self.extract_data_from_study(study_details)
                all_rows.extend(rows)
                processed_count += 1

                logger.info(f"Обработан тест {study_id}: {len(rows)} строк")

            except Exception as e:
                logger.error(f"Ошибка обработки теста {study_id}: {e}")
                continue

        logger.info(f"Обработано тестов: {processed_count}, пропущено: {skipped_count}, всего строк: {len(all_rows)}")

        # Шаг 4: Удаление дубликатов (study_id, campaign_id)
        all_rows = self._remove_duplicates(all_rows)

        return all_rows

    def _remove_duplicates(self, rows: List[Dict]) -> List[Dict]:
        """Удаление дубликатов по (study_id, campaign_id)"""
        seen = set()
        unique_rows = []

        for row in rows:
            key = (row['study_id'], row['campaign_id'])
            if key not in seen:
                seen.add(key)
                unique_rows.append(row)

        if len(unique_rows) < len(rows):
            logger.warning(f"Удалено дубликатов: {len(rows) - len(unique_rows)}")

        return unique_rows

    def save_to_csv(self, data: List[Dict], output_path: str):
        """Сохранение данных в CSV с соблюдением схемы эталона"""
        # Нормализация данных
        normalized_data = self.schema_manager.normalize_data(data)

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.schema_manager.column_order)
            writer.writeheader()
            writer.writerows(normalized_data)

        logger.info(f"Данные сохранены в {output_path}: {len(normalized_data)} строк")

    def run(self):
        """Основной метод выполнения"""
        try:
            # Обработка тестов
            data = self.process_all_studies()

            if not data:
                logger.warning("Нет данных для загрузки")
                return

            # Применение smoke режима
            if self.args.smoke:
                logger.info(f"Smoke режим: ограничение до {self.args.smoke} строк")
                data = data[:self.args.smoke]

            # Валидация схемы
            if not self.schema_manager.validate_data(data):
                logger.error("Данные не соответствуют схеме эталона")
                return

            # Сохранение в CSV
            temp_csv_path = 'temp_upload.csv'
            self.save_to_csv(data, temp_csv_path)

            # Dry-run режим
            if self.args.dry_run:
                logger.info("DRY-RUN режим: загрузка не выполняется")
                logger.info(f"Схема таблицы:\n{json.dumps(self.schema_manager.get_schema(), indent=2)}")
                logger.info(f"Статистика: {len(data)} строк готовы к загрузке")
                return

            # Создание/проверка таблицы
            self.api_client.create_or_update_table(
                self.args.table_name,
                self.schema_manager.get_schema()
            )

            # Загрузка данных
            upload_result = self.api_client.upload_data(self.args.table_name, temp_csv_path)

            # Логирование успешных загрузок
            for row in data:
                self.audit_logger.log_upload(
                    row['study_id'],
                    row['ds'],
                    'success',
                    f"Uploaded {len(data)} rows"
                )

            logger.info(f"Загрузка завершена успешно: {upload_result}")

            # Verify режим
            if self.args.verify:
                self._verify_upload(data)

        except Exception as e:
            logger.error(f"Критическая ошибка: {e}", exc_info=True)
            sys.exit(1)

    def _verify_upload(self, expected_data: List[Dict]):
        """Проверка корректности загрузки"""
        logger.info("Выполнение проверки загруженных данных...")

        try:
            # Запрос к таблице для проверки количества строк
            study_ids = {row['study_id'] for row in expected_data}
            study_ids_str = ','.join(f"'{sid}'" for sid in study_ids)

            query = f"SELECT study_id, COUNT(*) as cnt FROM {self.args.table_name} WHERE study_id IN ({study_ids_str}) GROUP BY study_id"
            result = self.api_client.query_table(query)

            if result:
                logger.info(f"Проверка: найдено {len(result)} тестов в таблице")
            else:
                logger.warning("Проверка: данные не найдены в таблице (возможно, требуется время на обработку)")

        except Exception as e:
            logger.error(f"Ошибка проверки: {e}")


def parse_args() -> argparse.Namespace:
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(
        description='Meta Advanced Analytics Uploader',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--days',
        type=int,
        default=14,
        help='Количество дней для фильтрации старых тестов (default: 14)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Проверка без загрузки, выводит схему и статистику'
    )

    parser.add_argument(
        '--verify',
        action='store_true',
        help='После загрузки сверяет, что строки появились в Meta'
    )

    parser.add_argument(
        '--smoke',
        type=int,
        metavar='N',
        help='Тестовая загрузка первых N строк'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Перезагрузка ранее загруженных тестов'
    )

    parser.add_argument(
        '--auto-evolve',
        action='store_true',
        help='Мягкое обновление схемы, если изменилась (NOT IMPLEMENTED)'
    )

    parser.add_argument(
        '--table-name',
        type=str,
        default='uploaded_ad_studies',
        help='Название таблицы в Meta Advanced Analytics'
    )

    return parser.parse_args()


def main():
    """Точка входа"""
    print("=" * 60)
    print("Meta Advanced Analytics Uploader")
    print("=" * 60)

    args = parse_args()

    try:
        config = Config()
        processor = DataProcessor(config, args)
        processor.run()

        print("\n" + "=" * 60)
        print("Выполнение завершено успешно")
        print("=" * 60)

    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
