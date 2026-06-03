# Media Access Policy

## Цель

Защитить приватные медиа наблюдений, не раздавать непроверенные справочные материалы и сохранить публичный доступ только к подтверждённым данным.

## Текущая политика доступа

1. `GET /api/media/observations/{filename}`
   - публично: только для `Observation.status=confirmed`
   - приватно (`on_review`, `needs_data`, `rejected`): доступ только
     - автору наблюдения
     - назначенному ревьюеру
     - ролям `ecologist`/`admin`

2. `GET /api/media/thumbnails/{filename}`
   - та же политика доступа, что и для оригиналов

3. `GET /api/media/species/{filename}`
   - публичные справочные материалы каталога только для файлов, прошедших аудит

4. `GET /api/media/species-pdf/{filename}`
   - legacy-route для старых извлечённых PDF-изображений
   - по умолчанию выключен: `SERVE_LEGACY_SPECIES_PDF_MEDIA=false`
   - вне development включать нельзя

5. `GET /api/media/species-audio/{filename}`
   - публичные аудио только для shipped-файлов из `backend/media/species-audio/SOURCES.md`
   - NC/ND/NC-SA источники исключены до отдельного письменного разрешения

## Хранение и выдача

- primary storage: MinIO (`bucket` из `MINIO_BUCKET`)
- fallback: локальный `media/` каталог
- ключи observation media валидируются по префиксу `observations/`
- ключи thumbnail валидируются по префиксу `thumbnails/`
- media API отдаёт файлы с `Content-Disposition: inline`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`, `Cross-Origin-Resource-Policy: same-origin`
- UI запрещает штатное контекстное меню/drag на видимых изображениях и убирает кнопку скачивания у audio controls через `controlsList="nodownload"`

Важно: это best-effort контроль, а не DRM. Если браузер отрисовал изображение или аудио, пользователь технически может сохранить его через инструменты разработчика, кеш, скриншот или запись экрана.

## Риски и контроль

- Риск: прямой доступ к непубличным observation media.
  - Контроль: access-check через связку `obs_media -> observation` и RBAC.
- Риск: утечка через некорректный ключ.
  - Контроль: ограничение формата/длины ключа + проверка префиксов.
- Риск: рост числа приватных ссылок с длинным TTL.
  - Контроль: для observation media задан короткий `Cache-Control`.
- Риск: показ непроверенных справочных фото.
  - Контроль: `media_rights_safe_20260603` очищает `photo_urls`, legacy `species-pdf` route выключен, старые бинарники удалены из поставки.
- Риск: использование аудио с NC/ND ограничениями.
  - Контроль: такие файлы удалены из поставки, seed/backfill очищает карточки видов, строки остаются в `docs/content-rights/media-audit.csv` как `permission_candidate`.

## Операционный чек

1. Проверить smoke-сценарии media access (public/private ACL).
2. Проверить, что `APP_ENV=production` и `ENABLE_DEV_AUTH=false`.
3. Проверить, что `MINIO_ROOT_USER/PASSWORD` не дефолтные.
4. Проверить, что приватные наблюдения недоступны анонимно.
5. Проверить, что `GET /api/media/species-pdf/page23_img07.png` возвращает 404 при настройке по умолчанию.
6. Проверить `docs/content-rights/media-audit.csv`: все `needs_permission/high` имеют `decision=remove_until_permission`, `hide_until_written_permission` или `exclude_until_permission`.
