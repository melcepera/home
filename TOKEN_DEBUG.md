## Почему токен может не работать (403 Forbidden)

### ✅ Что мы знаем:
- Token Valid: True
- Expires: через 2 месяца
- Permissions: ads_read, business_management, public_profile
- Длина: 198 символов (правильная)

### ❌ Возможные причины 403 Forbidden:

#### 1. **Версия API не совпадает** ⚠️ НАИБОЛЕЕ ВЕРОЯТНО
   - Мы используем: `v21.0`
   - Вы показывали примеры с: `v24.0`
   - **Решение:** Изменить версию API в скрипте

#### 2. **User не имеет роли в Business Manager**
   - Токен валиден, но пользователь не админ бизнеса
   - Проверить: https://business.facebook.com/settings/people
   - Ваша роль должна быть: Admin или Analyst

#### 3. **Business ID принадлежит другому аккаунту**
   - ID: 10152749513718373
   - Возможно это не ваш Business Manager
   - **Проверка:** откройте business.facebook.com и проверьте Business ID в URL

#### 4. **Приложение не имеет доступа к Business**
   - App ID: 1158622765593789
   - Приложение должно быть добавлено в Business Manager
   - Проверить: Business Settings → Apps

#### 5. **Скрытые символы в токене**
   - Пробелы, переводы строк, кавычки
   - **Проверка:** скопируйте токен прямо из Graph API Explorer

#### 6. **Permissions не применились корректно**
   - Хотя показаны в Token Info, реально не работают
   - **Решение:** Сгенерировать токен заново с явным выбором permissions

#### 7. **Rate Limiting или временная блокировка**
   - Слишком много запросов за короткое время
   - **Решение:** Подождать 15-30 минут

#### 8. **Endpoint требует другой тип токена**
   - `/ad_studies` может требовать App Access Token
   - Или System User Token вместо User Token

---

## 🔍 План диагностики:

### Шаг 1: Проверить версию API
```bash
curl "https://graph.facebook.com/v24.0/me?access_token=YOUR_TOKEN"
```

### Шаг 2: Проверить доступ к Business
```bash
curl "https://graph.facebook.com/v24.0/{BUSINESS_ID}?access_token=YOUR_TOKEN"
```

### Шаг 3: Проверить owned_ad_accounts
```bash
curl "https://graph.facebook.com/v24.0/{BUSINESS_ID}/owned_ad_accounts?access_token=YOUR_TOKEN"
```

### Шаг 4: Проверить прямой доступ к ad_studies
```bash
curl "https://graph.facebook.com/v24.0/{BUSINESS_ID}/ad_studies?fields=id,name&limit=1&access_token=YOUR_TOKEN"
```

---

## 💡 Самая частая причина:

**Неправильная версия API!**

В ваших примерах Graph API Explorer использовался `v24.0`,
а наш скрипт использует `v21.0`.

Давайте исправим это первым делом!
