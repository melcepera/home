#!/usr/bin/env python3
"""
Скрипт для получения списка доступных Dataset ID
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv('META_ACCESS_TOKEN')
BUSINESS_ID = os.getenv('META_BUSINESS_ID')

if not ACCESS_TOKEN or not BUSINESS_ID:
    print("Ошибка: META_ACCESS_TOKEN или META_BUSINESS_ID не установлены")
    exit(1)

print("=" * 60)
print("Поиск доступных датасетов...")
print("=" * 60)

# Попробуем получить датасеты для бизнеса
url = f"https://graph.facebook.com/v21.0/{BUSINESS_ID}"
params = {
    'fields': 'id,name',
    'access_token': ACCESS_TOKEN
}

try:
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    print("\nИнформация о бизнесе:")
    print(f"ID: {data.get('id')}")
    print(f"Name: {data.get('name', 'N/A')}")

except requests.exceptions.RequestException as e:
    print(f"Ошибка при запросе к API: {e}")
    if hasattr(e.response, 'text'):
        print(f"Ответ: {e.response.text}")

# Попробуем получить ad accounts
print("\n" + "=" * 60)
print("Получение Ad Accounts...")
print("=" * 60)

url = f"https://graph.facebook.com/v21.0/{BUSINESS_ID}/owned_ad_accounts"
params = {
    'fields': 'id,name,account_id',
    'access_token': ACCESS_TOKEN
}

try:
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    accounts = data.get('data', [])
    if accounts:
        print(f"\nНайдено Ad Accounts: {len(accounts)}")
        for acc in accounts[:5]:  # Показываем первые 5
            print(f"  - ID: {acc.get('id')}, Name: {acc.get('name', 'N/A')}")
    else:
        print("Ad Accounts не найдены")

except requests.exceptions.RequestException as e:
    print(f"Ошибка при запросе к API: {e}")
    if hasattr(e.response, 'text'):
        print(f"Ответ: {e.response.text}")

print("\n" + "=" * 60)
print("ИНСТРУКЦИЯ:")
print("=" * 60)
print("""
Для получения META_DATASET_ID:

1. Откройте Meta Advanced Analytics:
   https://www.facebook.com/analytics/

2. Выберите нужный датасет (или создайте новый)

3. Dataset ID будет в URL:
   https://www.facebook.com/analytics/<DATASET_ID>/overview

4. Скопируйте DATASET_ID и добавьте в .env файл

Или используйте один из Ad Account ID как dataset_id для тестирования.
""")
print("=" * 60)
