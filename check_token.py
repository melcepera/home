#!/usr/bin/env python3
"""
Проверка токена и доступных ресурсов
"""

import requests
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv('META_ACCESS_TOKEN')
BUSINESS_ID = os.getenv('META_BUSINESS_ID')

print("=" * 60)
print("ПРОВЕРКА ТОКЕНА")
print("=" * 60)

# 1. Проверка токена
print("\n1. Информация о токене:")
url = f"https://graph.facebook.com/v21.0/me"
params = {'access_token': TOKEN}

try:
    r = requests.get(url, params=params)
    print(f"Статус: {r.status_code}")
    print(f"Ответ: {r.json()}")
except Exception as e:
    print(f"Ошибка: {e}")

# 2. Проверка permissions
print("\n2. Права токена:")
url = f"https://graph.facebook.com/v21.0/me/permissions"
params = {'access_token': TOKEN}

try:
    r = requests.get(url, params=params)
    print(f"Статус: {r.status_code}")
    perms = r.json().get('data', [])
    for perm in perms:
        status = perm.get('status')
        name = perm.get('permission')
        print(f"  {name}: {status}")
except Exception as e:
    print(f"Ошибка: {e}")

# 3. Проверка доступа к бизнесу
print(f"\n3. Доступ к бизнесу {BUSINESS_ID}:")
url = f"https://graph.facebook.com/v21.0/{BUSINESS_ID}"
params = {'access_token': TOKEN}

try:
    r = requests.get(url, params=params)
    print(f"Статус: {r.status_code}")
    print(f"Ответ: {r.json()}")
except Exception as e:
    print(f"Ошибка: {e}")

# 4. Попробуем получить accounts
print(f"\n4. Ad Accounts:")
url = f"https://graph.facebook.com/v21.0/me/adaccounts"
params = {'access_token': TOKEN, 'fields': 'id,name'}

try:
    r = requests.get(url, params=params)
    print(f"Статус: {r.status_code}")
    accounts = r.json().get('data', [])
    if accounts:
        for acc in accounts[:5]:
            print(f"  {acc.get('id')}: {acc.get('name')}")
    else:
        print("  Нет доступных аккаунтов")
except Exception as e:
    print(f"Ошибка: {e}")

print("\n" + "=" * 60)
