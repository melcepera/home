#!/usr/bin/env python3
"""
Демо-версия Meta Advanced Analytics Uploader
Работает с моковыми данными для демонстрации
"""

import csv
import json
import logging
import sys
from datetime import datetime
from typing import List, Dict

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Моковые данные - похожие на реальные из Meta API
MOCK_STUDIES = [
    {
        "id": "783342637960013",
        "name": "Retargeting_FD_GP_Geo-WW_Payers-1_Inactive-7-180",
        "type": "LIFT",
        "start_time": "2025-10-10T00:00:32+0000",
        "end_time": "2025-10-24T00:00:31+0000",
        "cells": {
            "data": [
                {
                    "campaigns": {
                        "data": [
                            {
                                "id": "6689256263555",
                                "name": "Campaign Test 1",
                                "status": "ACTIVE"
                            }
                        ]
                    }
                }
            ]
        },
        "objectives": {
            "data": [
                {
                    "id": "749629461370229",
                    "name": "Purchase",
                    "type": "CONVERSIONS"
                },
                {
                    "id": "2321842278272824",
                    "name": "Initiate checkout",
                    "type": "CONVERSIONS"
                }
            ]
        }
    },
    {
        "id": "1449602592778359",
        "name": "Retargeting_GS_iOS_Geo-WW_Payers-45",
        "type": "LIFT",
        "start_time": "2025-10-15T00:00:15+0000",
        "end_time": "2025-11-07T01:00:14+0000",
        "cells": {
            "data": [
                {
                    "campaigns": {
                        "data": [
                            {
                                "id": "6795773503955",
                                "name": "Campaign Test 2",
                                "status": "ACTIVE"
                            },
                            {
                                "id": "6821989112355",
                                "name": "Campaign Test 3",
                                "status": "PAUSED"  # Будет отфильтрована
                            }
                        ]
                    }
                }
            ]
        },
        "objectives": {
            "data": [
                {
                    "id": "782050654580798",
                    "name": "fb_mobile_purchase",  # Нормализуется в Purchase
                    "type": "CONVERSIONS"
                },
                {
                    "id": "773342022531899",
                    "name": "initiated_checkout",  # Нормализуется в Initiate checkout
                    "type": "CONVERSIONS"
                },
                {
                    "id": "810497498086991",
                    "name": "Activate app",  # Будет проигнорирована
                    "type": "CONVERSIONS"
                }
            ]
        }
    },
    {
        "id": "1330643078501631",
        "name": "Old_Test_Expired",
        "type": "LIFT",
        "start_time": "2025-09-01T00:00:00+0000",
        "end_time": "2025-09-15T00:00:00+0000",  # Старый тест
        "cells": {
            "data": [
                {
                    "campaigns": {
                        "data": [
                            {
                                "id": "6689262540155",
                                "name": "Old Campaign",
                                "status": "ACTIVE"
                            }
                        ]
                    }
                }
            ]
        },
        "objectives": {
            "data": [
                {
                    "id": "638918032291663",
                    "name": "Purchase",
                    "type": "CONVERSIONS"
                }
            ]
        }
    }
]


class ObjectiveNormalizer:
    """Нормализация целей Meta"""

    PURCHASE_KEYWORDS = ['purchase', 'buy', 'fb_mobile_purchase', 'mobile_purchase']
    CHECKOUT_KEYWORDS = ['checkout', 'initiated_checkout', 'fb_mobile_initiated_checkout']

    @staticmethod
    def normalize_objective_name(raw_name: str) -> str:
        """Нормализация названия цели"""
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
        """Извлечение и нормализация целей"""
        objectives_data = study_details.get('objectives', {}).get('data', [])
        result = {
            'purchase_id': '',
            'session_id': ''
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


def filter_by_date(studies: List[Dict], days: int = 14) -> List[Dict]:
    """Фильтрация тестов по дате окончания"""
    cutoff_date = datetime.now()
    filtered = []

    for study in studies:
        end_time_str = study.get('end_time')
        if not end_time_str:
            filtered.append(study)
            continue

        try:
            end_time = datetime.fromisoformat(end_time_str.replace('+0000', ''))
            # Для демо проверяем что тест не закончился больше чем days дней назад
            days_ago = (cutoff_date - end_time).days

            if days_ago < days:
                filtered.append(study)
            else:
                logger.info(f"  Отфильтрован тест {study['id']}: закончился {days_ago} дней назад")
        except:
            filtered.append(study)

    return filtered


def has_active_campaigns(study: Dict) -> bool:
    """Проверка наличия активных кампаний"""
    cells = study.get('cells', {}).get('data', [])

    for cell in cells:
        campaigns = cell.get('campaigns', {}).get('data', [])
        for campaign in campaigns:
            if campaign.get('status') == 'ACTIVE':
                return True

    return False


def process_study(study: Dict) -> List[Dict]:
    """Обработка одного теста"""
    study_id = study.get('id')
    cells = study.get('cells', {}).get('data', [])

    # Извлекаем цели
    objectives = ObjectiveNormalizer.extract_objectives(study)
    objective_purchase_id = objectives['purchase_id']
    objective_session_id = objectives['session_id']

    # Текущая дата для ds
    ds = datetime.now().strftime('%Y-%m-%d')

    rows = []

    for cell in cells:
        campaigns = cell.get('campaigns', {}).get('data', [])

        for campaign in campaigns:
            campaign_status = campaign.get('status')

            # Игнорируем неактивные кампании
            if campaign_status in ['PAUSED', 'ARCHIVED', 'DELETED']:
                logger.info(f"    Пропущена кампания {campaign.get('id')}: статус {campaign_status}")
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
            logger.info(f"    ✓ Кампания {campaign_id}: purchase={objective_purchase_id}, session={objective_session_id}")

    return rows


def save_to_csv(data: List[Dict], output_path: str):
    """Сохранение данных в CSV"""
    columns = ['campaign_id', 'study_id', 'objective_purchase_id', 'objective_session_id', 'ds']

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(data)

    logger.info(f"\n✅ CSV файл создан: {output_path}")
    logger.info(f"   Строк: {len(data)}")


def main():
    logger.info("=" * 60)
    logger.info("ДЕМО: Meta Advanced Analytics Uploader")
    logger.info("=" * 60)

    logger.info("\n📊 Используются моковые данные для демонстрации\n")

    # Шаг 1: Фильтрация по дате
    logger.info("1️⃣ Фильтрация тестов по дате (последние 30 дней):")
    filtered_studies = filter_by_date(MOCK_STUDIES, days=30)
    logger.info(f"   Осталось тестов: {len(filtered_studies)} из {len(MOCK_STUDIES)}\n")

    # Шаг 2: Фильтрация по активным кампаниям
    logger.info("2️⃣ Фильтрация по активным кампаниям:")
    all_rows = []

    for study in filtered_studies:
        study_id = study.get('id')
        study_name = study.get('name')

        if not has_active_campaigns(study):
            logger.info(f"   Пропущен тест {study_id}: нет активных кампаний")
            continue

        logger.info(f"   Обработка теста {study_id}:")
        logger.info(f"     Название: {study_name}")

        rows = process_study(study)
        all_rows.extend(rows)

    # Шаг 3: Удаление дубликатов
    logger.info(f"\n3️⃣ Удаление дубликатов:")
    seen = set()
    unique_rows = []

    for row in all_rows:
        key = (row['study_id'], row['campaign_id'])
        if key not in seen:
            seen.add(key)
            unique_rows.append(row)

    if len(unique_rows) < len(all_rows):
        logger.info(f"   Удалено дубликатов: {len(all_rows) - len(unique_rows)}")
    else:
        logger.info(f"   Дубликатов не найдено")

    # Шаг 4: Сохранение в CSV
    logger.info(f"\n4️⃣ Сохранение в CSV:")
    output_file = 'demo_output.csv'
    save_to_csv(unique_rows, output_file)

    # Показать содержимое файла
    logger.info(f"\n📄 Содержимое файла {output_file}:")
    logger.info("-" * 60)
    with open(output_file, 'r') as f:
        content = f.read()
        print(content)
    logger.info("-" * 60)

    logger.info("\n" + "=" * 60)
    logger.info("✅ ДЕМО ЗАВЕРШЕНО")
    logger.info("=" * 60)
    logger.info("\nТеперь вы можете:")
    logger.info("1. Проверить файл demo_output.csv")
    logger.info("2. Подключить реальный Meta API с правильным токеном")
    logger.info("3. Запустить полную версию: python meta_analytics_uploader.py")


if __name__ == '__main__':
    main()
