# Offline Deploy Bundle

Этот способ нужен для контуров, где Docker не может сходить в Docker Hub или
другие внешние registry. На машине с нормальным доступом собирается архив с
готовыми Docker-образами. На корпоративном сервере Docker только загружает
готовый `.tar` через `docker load` и не скачивает пакеты из интернета.

## Что входит в пакет

- `images/green-book-nlmk-images.tar` — backend, frontend и support-образы
  PostGIS, Redis, MinIO.
- `docker-compose.offline.yml` — compose без `build` и без pull из registry.
- `.env.offline.example` — шаблон настроек для сервера.
- `install.sh` — загрузка образов, миграции, seed и запуск.
- `scripts/release_smoke.py` — post-deploy smoke.
- `CHECKSUMS.txt` — SHA-256 архива образов.

## Сборка пакета

Выполнять на машине, где Docker может скачать базовые образы и зависимости:

```bash
./scripts/build_offline_bundle.sh
```

По умолчанию пакет собирается под `linux/amd64`. Для явного указания
архитектуры:

```bash
PLATFORM=linux/amd64 ./scripts/build_offline_bundle.sh
```

Опционально можно задать тег:

```bash
TAG=2026-06-03 PLATFORM=linux/amd64 ./scripts/build_offline_bundle.sh
```

Готовый архив появится в `dist/offline/green-book-nlmk-offline-<tag>.tar.gz`.

## Установка на сервере

Скопировать архив на сервер и распаковать:

```bash
tar -xzf green-book-nlmk-offline-<tag>.tar.gz
cd green-book-nlmk-offline-<tag>
```

Подготовить `.env`:

```bash
cp .env.offline.example .env
vi .env
```

Обязательно заменить:

- `AUTH_SECRET_KEY`
- `POSTGRES_PASSWORD` и пароль внутри `DATABASE_URL`
- `MINIO_ROOT_USER`
- `MINIO_ROOT_PASSWORD`
- `BOOTSTRAP_ADMIN_LOGIN`
- `BOOTSTRAP_ADMIN_PASSWORD`
- `BOOTSTRAP_ADMIN_DISPLAY_NAME`
- `CORS_ORIGINS`
- `YMAPS_API_KEY`

`BACKEND_IMAGE`, `FRONTEND_IMAGE`, `DB_IMAGE`, `REDIS_IMAGE` и `MINIO_IMAGE`
обычно уже попадают в `.env.offline.example` при сборке пакета. Если `.env`
создавался вручную и эти значения пропущены, `install.sh` возьмёт их из
`manifest.env` рядом с архивом. Не подставляйте placeholder вида
`your-registry/...`, если установка идёт через `docker load` из offline-пакета:
нужны ровно те имена образов, которые указаны в `manifest.env`.

Запустить:

```bash
./install.sh
```

Если образы уже загружены и нужно только перезапустить стек:

```bash
./install.sh --skip-load --skip-migrations --skip-seed
```

## Проверки после запуска

Проверить liveness:

```bash
curl -fsS http://127.0.0.1:5173/api/health
```

Ожидается HTTP `200` и `status=ok`.

Проверить readiness:

```bash
curl -fsS http://127.0.0.1:5173/api/health/ready
```

Ожидается HTTP `200`, `status=ready`, зависимости `database`, `redis`, `minio`
в состоянии `connected`.

Быстрый smoke:

```bash
python3 scripts/release_smoke.py --base-url http://127.0.0.1:5173
```

Для полного write-smoke:

```bash
python3 scripts/release_smoke.py \
  --base-url http://127.0.0.1:5173 \
  --admin-login "$BOOTSTRAP_ADMIN_LOGIN" \
  --admin-password "$BOOTSTRAP_ADMIN_PASSWORD" \
  --exercise-write-workflow
```

## Важные ограничения

- Серверу всё равно нужны установленные Docker и Docker Compose.
- Пакет должен собираться под совместимую архитектуру сервера. Для обычного
  Linux x86_64 используйте `PLATFORM=linux/amd64`.
- Если корпоративная политика требует внутренний registry, этот же пакет можно
  использовать как промежуточный: `docker load`, затем `docker tag` и
  `docker push` во внутренний registry.
- `docker-compose.offline.yml` использует `pull_policy: never`, поэтому при
  отсутствии образа запуск должен упасть сразу, а не пытаться идти во внешний
  registry.
- `install.sh` выполняет одноразовые команды через `docker compose run -T`.
  Это важно для серверов, где скрипт запускается без интерактивного TTY; без
  `-T` Docker Compose может завершиться ошибкой `the input device is not a TTY`.
