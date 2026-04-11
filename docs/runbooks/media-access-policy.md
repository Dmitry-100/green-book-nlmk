# Media Access Policy

## Цель

Защитить приватные медиа наблюдений и сохранить публичный доступ только к подтверждённым данным.

## Текущая политика доступа

1. `GET /api/media/observations/{filename}`
   - публично: только для `Observation.status=confirmed`
   - приватно (`on_review`, `needs_data`, `rejected`): доступ только
     - автору наблюдения
     - назначенному ревьюеру
     - ролям `ecologist`/`admin`

2. `GET /api/media/thumbnails/{filename}`
   - та же политика доступа, что и для оригиналов

3. `GET /api/media/species/{filename}` и `GET /api/media/species-pdf/{filename}`
   - публичные справочные материалы каталога

## Хранение и выдача

- primary storage: MinIO (`bucket` из `MINIO_BUCKET`)
- fallback: локальный `media/` каталог
- ключи observation media валидируются по префиксу `observations/`
- ключи thumbnail валидируются по префиксу `thumbnails/`

## Риски и контроль

- Риск: прямой доступ к непубличным observation media.
  - Контроль: access-check через связку `obs_media -> observation` и RBAC.
- Риск: утечка через некорректный ключ.
  - Контроль: ограничение формата/длины ключа + проверка префиксов.
- Риск: рост числа приватных ссылок с длинным TTL.
  - Контроль: для observation media задан короткий `Cache-Control`.

## Операционный чек

1. Проверить smoke-сценарии media access (public/private ACL).
2. Проверить, что `APP_ENV=production` и `ENABLE_DEV_AUTH=false`.
3. Проверить, что `MINIO_ROOT_USER/PASSWORD` не дефолтные.
4. Проверить, что приватные наблюдения недоступны анонимно.
