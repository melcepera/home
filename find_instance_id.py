#!/usr/bin/env python3
"""
Поиск Meta Advanced Analytics Instance ID
"""

import requests
from dotenv import load_dotenv
import os
import json

load_dotenv()

TOKEN = os.getenv('META_ACCESS_TOKEN')
BUSINESS_ID = os.getenv('META_BUSINESS_ID')

print("=" * 60)
print("ПОИСК META ADVANCED ANALYTICS INSTANCE ID")
print("=" * 60)

if not TOKEN or not BUSINESS_ID:
    print("\n⚠️  Ошибка: META_ACCESS_TOKEN или META_BUSINESS_ID не установлены")
    exit(1)

# Способ 1: Попробуем получить через business
print(f"\n📍 Способ 1: Через Business ID ({BUSINESS_ID})")
print("-" * 60)

url = f"https://graph.facebook.com/v21.0/{BUSINESS_ID}"
params = {
    'fields': 'id,name,analytics_instances',
    'access_token': TOKEN
}

try:
    response = requests.get(url, params=params, timeout=30)
    print(f"Статус: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Business Name: {data.get('name', 'N/A')}")

        instances = data.get('analytics_instances', {}).get('data', [])
        if instances:
            print(f"\n✅ Найдено Analytics Instances: {len(instances)}")
            for inst in instances:
                print(f"\n  Instance ID: {inst.get('id')}")
                print(f"  Name: {inst.get('name', 'N/A')}")
                print(f"  ---")
        else:
            print("❌ Analytics instances не найдены через этот метод")
    else:
        print(f"❌ Ошибка: {response.text}")

except Exception as e:
    print(f"❌ Ошибка запроса: {e}")

# Способ 2: Попробуем через me
print(f"\n📍 Способ 2: Через /me/analytics_platforms")
print("-" * 60)

url = f"https://graph.facebook.com/v21.0/me/analytics_platforms"
params = {
    'access_token': TOKEN
}

try:
    response = requests.get(url, params=params, timeout=30)
    print(f"Статус: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        platforms = data.get('data', [])

        if platforms:
            print(f"\n✅ Найдено Analytics Platforms: {len(platforms)}")
            for platform in platforms:
                print(f"\n  Platform ID: {platform.get('id')}")
                print(f"  Name: {platform.get('name', 'N/A')}")
                print(f"  ---")
        else:
            print("❌ Analytics platforms не найдены")
    else:
        print(f"❌ Ошибка: {response.text}")

except Exception as e:
    print(f"❌ Ошибка запроса: {e}")

# Способ 3: Проверим owned_pixels (может быть связан с Analytics)
print(f"\n📍 Способ 3: Через Pixel (может быть связан с Analytics)")
print("-" * 60)

url = f"https://graph.facebook.com/v21.0/{BUSINESS_ID}/owned_pixels"
params = {
    'fields': 'id,name',
    'access_token': TOKEN
}

try:
    response = requests.get(url, params=params, timeout=30)
    print(f"Статус: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        pixels = data.get('data', [])

        if pixels:
            print(f"\n✅ Найдено Pixels: {len(pixels)}")
            for pixel in pixels:
                print(f"\n  Pixel ID: {pixel.get('id')}")
                print(f"  Name: {pixel.get('name', 'N/A')}")
                print(f"  ---")
        else:
            print("❌ Pixels не найдены")
    else:
        print(f"❌ Ошибка: {response.text}")

except Exception as e:
    print(f"❌ Ошибка запроса: {e}")

print("\n" + "=" * 60)
print("ИНСТРУКЦИЯ ПО ПОИСКУ INSTANCE_ID")
print("=" * 60)
print("""
Если автоматический поиск не сработал, найдите вручную:

1. 📱 Через веб-интерфейс Meta Advanced Analytics:

   a) Откройте: https://www.facebook.com/analytics/

   b) Выберите ваш датасет/app из списка

   c) Посмотрите в URL адресной строки:
      https://www.facebook.com/analytics/<INSTANCE_ID>/overview

   d) Скопируйте INSTANCE_ID из URL

2. 🔍 Альтернатива - через Business Manager:

   a) Откройте: https://business.facebook.com/settings/

   b) Data Sources → Datasets

   c) Найдите нужный датасет и скопируйте его ID

3. 📊 Если у вас нет Advanced Analytics instance:

   Возможно, вам нужно сначала создать его:
   - Events Manager → Data Sources → Create Dataset
   - Или использовать существующий Pixel ID как альтернативу

После нахождения ID добавьте в .env файл:
META_INSTANCE_ID=ваш_instance_id_здесь

Или используйте Pixel ID (из списка выше) для тестирования.
""")
print("=" * 60)
