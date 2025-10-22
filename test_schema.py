#!/usr/bin/env python3
"""
Тестовый скрипт для проверки схемы таблицы
"""

import csv
import json

def load_schema_from_csv(csv_path):
    """Загрузка схемы из эталонного CSV"""
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        column_order = reader.fieldnames

        # Определяем типы данных из первой строки
        first_row = next(reader, None)

        columns = []
        for col_name in column_order:
            value = first_row.get(col_name, '') if first_row else ''

            # Определяем тип
            if col_name == 'ds' or 'date' in col_name.lower():
                col_type = 'date'
            elif col_name.endswith('_id'):
                col_type = 'string'
            elif value and value.replace('.', '').replace('-', '').isdigit():
                col_type = 'double' if '.' in value else 'integer'
            else:
                col_type = 'string'

            columns.append({
                'name': col_name,
                'type': col_type
            })

        return columns, column_order

# Загружаем схему
schema, columns = load_schema_from_csv('reference.csv')

print("=" * 60)
print("СХЕМА ТАБЛИЦЫ: automate_match_chain_campaign_study_objective")
print("=" * 60)
print("\nСтруктура для Meta Advanced Analytics Create Table API:\n")
print(json.dumps(schema, indent=2, ensure_ascii=False))

print("\n" + "=" * 60)
print("ПОРЯДОК КОЛОНОК:")
print("=" * 60)
for i, col in enumerate(columns, 1):
    schema_col = schema[i-1]
    print(f"{i}. {col:30s} [{schema_col['type']}]")

print("\n" + "=" * 60)
print("ИТОГО:")
print("=" * 60)
print(f"Колонок: {len(columns)}")
print(f"Название таблицы: automate_match_chain_campaign_study_objective")
print("=" * 60)
