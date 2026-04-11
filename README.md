# Зелёная книга ПАО «НЛМК»

Интерактивный портал для фиксации и валидации наблюдений за растительным и животным миром на промышленной площадке ПАО «НЛМК» (г. Липецк).

Проект превращает статичный PDF-каталог «Зелёная книга» (193 вида, 32 страницы) в живую веб-платформу, где сотрудники наблюдают за природой, экологи валидируют находки, а все данные собираются на интерактивной карте. Встроенная система геймификации мотивирует сотрудников участвовать в наблюдениях.

---

## Скриншоты

### Главная страница
Hero-секция с лебедем из обложки «Зелёной книги», статистика в реальном времени, карточки 6 групп с фотографиями, «Вид месяца» с челленджем, «Факт дня», каталог видов и лента последних находок.

![Главная страница](docs/screenshots/01-home.png)

### Справочник видов
189 видов из «Зелёной книги» с фотографиями, фильтрами по группе/категории и поиском по названию (русскому и латинскому).

![Справочник видов](docs/screenshots/02-species-list.png)

### Карточка вида
Детальная информация о виде: фотография, группа, категория, охранный статус, описание, правила поведения. Блок «Первооткрыватель» — кто первым подтвердил наблюдение вида на площадке.

![Карточка вида](docs/screenshots/03-species-detail.png)

### Форма наблюдения
Выбор группы по фотографиям (3 колонки), дата/время, место на Яндекс Карте с маркером (клик или перетаскивание), загрузка фото/видео, чекбокс техники безопасности.

![Форма наблюдения](docs/screenshots/04-observe.png)

### Мои наблюдения
Список наблюдений сотрудника с фотографиями, статусами (на проверке / подтверждено / отклонено / нужны данные) и фильтрацией. Клик открывает детальную страницу.

![Мои наблюдения](docs/screenshots/05-my-observations.png)

### Карта наблюдений
Яндекс Карты с кластеризацией точек наблюдений, фильтрами по группе и статусу, легендой и списком наблюдений в боковой панели.

![Карта наблюдений](docs/screenshots/06-map.png)

### Определитель видов
Пошаговый wizard: выбор группы по фотографии, затем сетка видов с фото для идентификации. Помогает сотрудникам определить, что они встретили.

![Определитель видов](docs/screenshots/07-identify.png)

### Форма инцидента
Режим инцидента — для экстренных ситуаций (раненое/погибшее животное). Автоматически активируется при переходе с кнопки «Инцидент». Тип и серьёзность инцидента.

![Форма инцидента](docs/screenshots/08-incident.png)

### Правила и помощь
Инструкции по технике безопасности, создание наблюдений, определение видов, статусы, контакты Управления технического заказчика.

![Правила и помощь](docs/screenshots/09-help.png)

### Профиль и геймификация
Личный профиль сотрудника: баллы, количество наблюдений, видов, открытий. Заработанные достижения (бейджи). Лидерборд с фильтром по периоду (месяц/квартал/год/всё время). Факт дня.

![Профиль](docs/screenshots/10-profile.png)

### Викторина «Угадай вид»
Показывается фото из каталога — нужно выбрать правильное название из 4 вариантов. Счётчик правильных ответов и серий.

![Викторина](docs/screenshots/11-quiz.png)

### Экологический паспорт площадки
Индекс биоразнообразия Шеннона (с тултипом-справкой), видовой состав по группам с фотографиями, график сезонной динамики (текущий месяц выделен), фотогалерея представителей, карта наблюдений.

![Экопаспорт](docs/screenshots/12-passport.png)

### Маршруты наблюдений
5 рекомендованных маршрутов по территории площадки: описание, дистанция, время, сложность, какие виды можно встретить, советы, лучшее время. Напоминание о технике безопасности.

![Маршруты](docs/screenshots/13-routes.png)

### Детали наблюдения
Фотография, вид, группа, статус, карта с точкой наблюдения (Яндекс Карты). Лайки и комментарии — социальные механики для обсуждения находок.

![Детали наблюдения](docs/screenshots/14-observation-detail.png)

### Кабинет эколога
Очередь валидации с табами по статусам. Подтверждение, отклонение, запрос уточнений. Доступен только пользователям с ролью «Эколог» или «Администратор».

![Кабинет эколога](docs/screenshots/15-expert.png)

### Админ-панель
Управление справочником видов, импорт GeoJSON зон площадки, аудит-действий и операционная сводка. Доступна только администраторам.

![Админ-панель](docs/screenshots/16-admin.png)

### Вход (dev-режим)
Выбор роли для разработки (Сотрудник / Эколог / Администратор). В продакшене — вход через корпоративный SSO (Blitz Identity Provider).

![Вход](docs/screenshots/17-login.png)

---

## Геймификация

Система мотивации поощряет сотрудников активно наблюдать за природой на территории площадки.

### Как работает

1. **Сотрудник** создаёт наблюдение: выбирает группу, ставит точку на карте, загружает фото
2. **Эколог** проверяет и подтверждает наблюдение
3. При подтверждении автоматически:
   - Начисляются **баллы** (1-30 за наблюдение)
   - Проверяются условия **достижений** (11 бейджей)
   - Записывается **первооткрыватель** вида (если вид обнаружен впервые)

### Баллы

| Категория вида | Базовые баллы |
|---|---|
| Типичный / синантроп / рудеральный | 1 |
| Редкий | 5 |
| Красная книга | 10 |

**Множители:**
- **×3** — первое наблюдение вида на площадке (first discovery)
- **×2** — наблюдение в правильный сезон для вида

### Достижения (11 бейджей)

| Бейдж | Условие | Баллы |
|---|---|---|
| 🌱 Первые шаги | Первое подтверждённое наблюдение | +10 |
| 🔬 Натуралист | 10 подтверждённых наблюдений | +50 |
| 🏆 Эксперт | 50 подтверждённых наблюдений | +200 |
| 🌈 Все группы | Наблюдения из каждой из 6 групп | +100 |
| 💎 Редкая находка | Наблюдение вида из Красной книги | +50 |
| 🌅 Ранняя пташка | Наблюдение до 7:00 утра | +20 |
| 🌙 Ночной дозор | Наблюдение после 22:00 | +20 |
| 🍂 Сезонный охотник | Наблюдения в 4 разных сезона | +100 |
| 📸 Фотограф | 5 наблюдений с фото | +30 |
| 🚨 Спасатель | Сообщение об инциденте | +30 |
| 🏅 Первооткрыватель | Первое наблюдение нового вида | +100 |

### Челлендж месяца

Каждый месяц на главной странице выделяется целевой вид из Красной книги. Кто первый найдёт и подтвердит наблюдение — получает специальный бейдж.

### Лидерборд

Рейтинг наблюдателей по баллам с фильтрацией по периоду: месяц, квартал, год, всё время. Топ-3 выделены золотом, серебром и бронзой.

### Социальные механики

- **Комментарии** к наблюдениям — эколог может похвалить, коллеги могут спросить совет
- **Лайки** на наблюдения — отмечайте интересные находки
- **Лента «Последние находки»** на главной — свежие подтверждённые наблюдения

---

## Образование

### Викторина «Угадай вид»
Показывается фото из каталога — нужно выбрать правильное название из 4 вариантов (предпочтительно из той же группы). Счётчик правильных ответов и серий подряд.

### Факт дня
Случайный вид из каталога с описанием — на главной странице и в профиле. Меняется при каждом заходе.

### Определитель видов
Пошаговый визард: выбор группы по фотографии → сетка видов для идентификации.

### Маршруты наблюдений
5 рекомендованных маршрутов по территории: пруд-охладитель (водоплавающие), лесополоса (мелкие птицы), степной участок (насекомые, ящерицы), шлакоотвал (рекультивация), ночной маршрут (летучие мыши, ежи).

---

## Экологический паспорт

Аналитическая страница для ESG-отчётности и мониторинга биоразнообразия:

- **Индекс Шеннона** (H') — мера биоразнообразия: H' = -Σ(pᵢ × ln pᵢ). Шкала: <1 низкое, 1-2 среднее, 2-3 высокое, >3 очень высокое
- **Видовой состав по группам** — столбчатая диаграмма с фото
- **Сезонная динамика** — количество видов по месяцам
- **Карта наблюдений** — точки наблюдений с цветовой кодировкой по группам

---

## Архитектура

```
┌─────────────────────────────────────────────────┐
│              Битрикс (nlmk.one)                 │
│  ┌───────────┐  ┌────────────────────────────┐  │
│  │ SSO/Auth  │  │  Vue.js SPA                │  │
│  │ (Blitz    │  │  «Животный и растительный  │  │
│  │  OAuth)   │  │   мир»                     │  │
│  └─────┬─────┘  └─────────────┬──────────────┘  │
└────────┼──────────────────────┼──────────────────┘
         │ JWT/token            │ REST API
         ▼                     ▼
┌─────────────────────────────────────────────────┐
│           FastAPI Backend                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │Наблюдения│ │Справочник│ │ Geo-сервис       │ │
│  │& инцид.  │ │видов     │ │ (зоны, point-in- │ │
│  │          │ │          │ │  polygon)        │ │
│  └────┬─────┘ └────┬─────┘ └───────┬──────────┘ │
│       │            │               │            │
│  ┌────┴────────────┴───────────────┴──────────┐ │
│  │         SQLAlchemy + GeoAlchemy2           │ │
│  └────────────────────┬───────────────────────┘ │
└───────────────────────┼─────────────────────────┘
                        │
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
   ┌──────────┐  ┌──────────┐  ┌──────────┐
   │PostgreSQL│  │  MinIO   │  │  Redis   │
   │+ PostGIS │  │  (медиа) │  │(кэш,     │
   │          │  │          │  │ сессии)  │
   └──────────┘  └──────────┘  └──────────┘
```

---

## Технологический стек

| Компонент | Технология |
|---|---|
| **Backend** | Python 3.12, FastAPI, SQLAlchemy 2.0, GeoAlchemy2, Alembic |
| **Frontend** | Vue 3, TypeScript, Vite, Pinia, Vue Router, Element Plus |
| **БД** | PostgreSQL 16 + PostGIS 3.4 |
| **Карты** | Яндекс Карты JS API 2.1 |
| **Медиа** | MinIO (S3-совместимое хранилище) |
| **Кэш** | Redis 7 |
| **Инфраструктура** | Docker, Docker Compose |
| **Аутентификация** | JWT (Blitz SSO в продакшене) |

---

## API-эндпоинты (35+)

| Группа | Эндпоинты | Описание |
|---|---|---|
| **Health** | `GET /api/health` | Проверка состояния |
| **Species** | `GET/POST /api/species`, `GET/PUT/DELETE /api/species/{id}` | CRUD справочника видов |
| **Observations** | `POST/GET /api/observations`, `GET /my`, `GET/{id}`, `PATCH/{id}` | Наблюдения сотрудников |
| **Comments** | `GET/POST /api/observations/{id}/comments` | Комментарии к наблюдениям |
| **Likes** | `GET/POST /api/observations/{id}/likes`, `GET /{id}/likes/me` | Лайки наблюдений |
| **Media** | `POST /api/observations/upload-url`, `POST /{id}/media` | Загрузка медиа через presigned URL |
| **Validation** | `GET /queue`, `POST /{id}/confirm\|reject\|request-data` | Валидация экологом |
| **Notifications** | `GET`, `PATCH /{id}/read`, `GET /unread-count` | Уведомления |
| **Map** | `GET /observations`, `GET /zones`, `GET /zone-by-point` | GeoJSON для карты |
| **Gamification** | `GET /leaderboard\|profile\|stats\|challenge\|quiz\|fact-of-day` | Геймификация |
| **Identifier** | `GET /tree`, `POST /suggest` | Дерево определителя |
| **Export** | `GET /observations` | Выгрузка в XLSX |
| **Admin** | `POST /zones/import`, `GET /audit/events`, `POST /audit/purge`, `GET /ops/summary`, `GET /ops/alerts` | Импорт зон, audit trail и операционный контроль |
| **Config** | `GET /config/ymaps` | API-ключ карт |
| **Dev Auth** | `POST /dev/token` | JWT для разработки |

---

## Страницы (17)

| Путь | Страница | Описание |
|---|---|---|
| `/` | Главная | Hero, статистика, вид месяца с челленджем, факт дня, каталог, лента находок |
| `/species` | Справочник видов | 189 видов, фильтры, поиск |
| `/species/:id` | Карточка вида | Фото, описание, статус, первооткрыватель |
| `/observe` | Новое наблюдение | Форма с картой, фото, группой |
| `/my` | Мои наблюдения | Список со статусами и фото |
| `/observations/:id` | Детали наблюдения | Фото, карта, комментарии, лайки |
| `/map` | Карта наблюдений | Яндекс Карты + кластеризация |
| `/identify` | Определитель | Wizard с фото для идентификации |
| `/quiz` | Викторина | «Угадай вид» по фото |
| `/passport` | Экопаспорт | Индекс Шеннона, графики, галерея |
| `/routes` | Маршруты | 5 маршрутов наблюдений |
| `/profile` | Профиль | Баллы, достижения, лидерборд |
| `/expert` | Кабинет эколога | Очередь валидации |
| `/admin` | Администрирование | Виды, зоны, роли |
| `/help` | Правила и помощь | ТБ, инструкции, контакты |
| `/login` | Вход (dev) | Выбор роли |

---

## Ролевая модель

| Роль | Возможности | Навигация |
|---|---|---|
| **Сотрудник** | Создание наблюдений, просмотр каталога и карты, викторина, профиль | Все вкладки кроме «Эколог» и «Админ» |
| **Эколог** | + Валидация наблюдений, экспорт данных | + вкладка «Эколог» |
| **Администратор** | + Управление справочниками, импорт зон | + вкладки «Эколог» и «Админ» |

---

## Данные

- **189 видов** из «Зелёной книги ПАО НЛМК» (PDF, 32 стр.)
- **6 групп**: растения (49), грибы (15), насекомые (45), герпетофауна (14), птицы (45), млекопитающие (21)
- **189 описаний** — научно-популярные тексты для каждого вида
- **194 фотографии** — извлечены из PDF каталога
- **49 узлов** дерева определителя для всех 6 групп
- **11 достижений** — бейджи с условиями и бонусными баллами
- **5 маршрутов** — рекомендованные маршруты наблюдений

---

## Быстрый старт

### Требования
- Docker и Docker Compose
- API-ключ Яндекс Карт (v2.1)

### Запуск

```bash
# Клонировать
git clone https://github.com/Dmitry-100/green-book-nlmk.git
cd green-book-nlmk

# Настроить окружение
cp .env.example .env
# Отредактировать .env — добавить YMAPS_API_KEY

# Запустить все сервисы
docker compose up --build -d

# Применить миграции
docker compose exec backend alembic upgrade head

# Загрузить данные
docker compose exec backend python -m app.seed.run_seed
docker compose exec backend python -m app.seed.seed_tree
docker compose exec backend python -m app.seed.seed_achievements
docker compose exec backend python -m app.seed.seed_demo
```

### Доступ

| Сервис | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| MinIO Console | http://localhost:9001 |
| Dev Login | http://localhost:5173/login |

---

## Эксплуатация

### Проверки здоровья

- `GET /api/health` — liveness (приложение + БД)
- `GET /api/health/ready` — readiness (БД + Redis + MinIO)
- `GET /api/health/deps` — расширенный dependency snapshot (latency + cache health)

### Логи и мониторинг

- Логи backend — структурированные JSON (stdout)
- Корреляция запросов через `X-Request-ID`
- Опциональный Sentry (указать `SENTRY_DSN`)
- Runtime-метрики API: `GET /api/metrics` (доступно только `admin`)
- Prometheus-формат метрик: `GET /api/metrics/prometheus` (доступно только `admin`)
- Операционная сводка: `GET /api/admin/ops/summary` (доступно только `admin`)
- Пороговые оповещения: `GET /api/admin/ops/alerts` (доступно только `admin`)
- runbook: `docs/runbooks/observability-v2.md`

### Проверки качества

```bash
# Статический анализ backend
docker compose exec backend ruff check app tests

# Автотесты backend
docker compose exec backend pytest -q
```

- В основном `CI` дополнительно выполняются:
  - проверка workflow/compose конфигов (`workflow-config`)
  - проверка интерфейса restore-drill скрипта (`security-fast`)
  - backend/frontend tests публикуют coverage artifacts (`backend-coverage`, `frontend-coverage`)
- Security scan workflow: `.github/workflows/security-scans.yml`
  - backend dependency audit (`pip-audit`)
  - frontend dependency audit (`npm audit`)
  - secret scanning (`gitleaks`)

### Post-deploy smoke

```bash
# Быстрая проверка задеплоенного API
python scripts/release_smoke.py --base-url https://api.example.com

# С admin-проверками
python scripts/release_smoke.py \
  --base-url https://api.example.com \
  --admin-token "<admin-bearer-token>"
```

- Для CI доступен manual workflow: `.github/workflows/post-deploy-smoke.yml`
- В `CI` pipeline дополнительно выполняется release smoke публичных endpoint'ов.
- Для периодического мониторинга доступен workflow: `.github/workflows/ops-heartbeat.yml`
  (использует `OPS_BASE_URL` и опционально `SMOKE_ADMIN_TOKEN` из GitHub Secrets).
  Workflow запускает smoke с флагом `--fail-on-ops-alerts`, чтобы ловить превышение порогов в `/api/admin/ops/alerts`.
- Для CD в test/staging:
  - `.github/workflows/cd-build-publish.yml` — build/publish backend/frontend image в GHCR
  - `.github/workflows/deploy-staging.yml` — deploy на staging (migrations + smoke + rollback path)
  - `.github/workflows/deploy-rehearsal.yml` — регулярная репетиция deploy + rollback в изолированном окружении
  - release checklist: `docs/runbooks/release-checklist.md`

### Профилирование производительности

```bash
# Сгенерировать синтетический набор наблюдений для нагрузочного профиля
./scripts/perf_seed_observations.sh 100000

# Быстрый профиль API (RPS + latency p50/p95/p99)
python scripts/perf_api.py \
  --path /api/dashboard/summary \
  --path '/api/gamification/stats?heatmap_limit=1200' \
  --path '/api/map/observations?limit=1200' \
  --requests 200 \
  --concurrency 20

# Удалить синтетические benchmark-данные
./scripts/perf_seed_observations.sh --cleanup
```

### Production-like perf профиль (Docker Compose)

```bash
# Поднять стек в режиме perf (production-like backend без reload, workers, rate-limit off)
docker compose -f docker-compose.yml -f docker-compose.perf.yml up --build -d

# Прогнать профиль
python scripts/perf_api.py \
  --path /api/dashboard/summary \
  --path '/api/gamification/stats?heatmap_limit=1200' \
  --path '/api/map/observations?limit=1200' \
  --requests 200 \
  --concurrency 20

# Остановить perf-профиль
docker compose -f docker-compose.yml -f docker-compose.perf.yml down
```

### Бэкапы БД

```bash
# Создать backup (SQL.gz)
./scripts/backup_db.sh

# Восстановить БД из backup
./scripts/restore_db.sh backups/db/greenbook_YYYYMMDD_HHMMSS.sql.gz

# Restore drill (RTO/RPO + smoke)
./scripts/restore_drill.sh --base-url http://localhost:8000

# Staging deploy rehearsal (изолированный compose-проект)
PROJECT_NAME=greenbook-rehearsal \
STAGING_BACKEND_PORT=18000 \
./scripts/staging_deploy_rehearsal.sh --base-url http://127.0.0.1:18000

# Оставить rehearsal-контур поднятым для ручной диагностики
PROJECT_NAME=greenbook-rehearsal \
STAGING_BACKEND_PORT=18000 \
./scripts/staging_deploy_rehearsal.sh --base-url http://127.0.0.1:18000 --keep-stack
```

- Scheduled restore drill workflow: `.github/workflows/restore-drill.yml`
- Release/restore runbooks:
  - `docs/runbooks/release-checklist.md`
  - `docs/runbooks/observability-v2.md`
  - `docs/runbooks/media-access-policy.md`

### Миграции БД

```bash
# Применить все миграции Alembic к текущей БД и вывести текущую revision
./scripts/migrate_db.sh
```

### Ретеншн audit-логов

```bash
# Проверить, сколько записей audit_logs старше 180 дней
./scripts/purge_audit_logs.sh --dry-run

# Удалить audit_logs старше 180 дней
./scripts/purge_audit_logs.sh --days 180
```

- API для админа: `POST /api/admin/audit/purge` (параметры `older_than_days`, `dry_run`)
- Перед запуском SQL-скрипта убедитесь, что миграция `audit_logs` применена в целевой БД.

### Ежедневный maintenance

```bash
# Прогон в режиме dry-run
./scripts/maintenance_daily.sh --dry-run

# Полный запуск (backup + purge audit по AUDIT_LOG_RETENTION_DAYS)
./scripts/maintenance_daily.sh
```

Пример cron (ежедневно в 03:15):

```bash
15 3 * * * cd /path/to/green-book-nlmk && ./scripts/maintenance_daily.sh >> ./backups/db/maintenance.log 2>&1
```

### Продакшен-чеклист окружения

- `APP_ENV=production`
- `ENABLE_DEV_AUTH=false`
- `AUTH_SECRET_KEY` — уникальный секрет (не дефолтный)
- `CORS_ORIGINS` — список разрешённых доменов без `*`
- `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` — не дефолтные значения
- `API_RATE_LIMIT_ENABLED=true`
- Rate limiting учитывает `JWT sub` для авторизованных пользователей (изоляция лимитов между пользователями за одним IP/NAT).
- `MAP_OBSERVATIONS_CACHE_TTL_SECONDS` — короткий TTL для повторяющихся bbox-запросов карты (обычно `5..20`)
- `SPECIES_LIST_CACHE_TTL_SECONDS` — TTL server-side cache для `/api/species` (обычно `60..300`)
- `VALIDATION_QUEUE_CACHE_TTL_SECONDS` — TTL server-side cache очереди валидации (обычно `5..30`)
- `NOTIFICATION_UNREAD_CACHE_TTL_SECONDS` — TTL cache для `/api/notifications/unread-count` (обычно `5..20`)
- `AUDIT_LOG_RETENTION_DAYS` — базовый порог ретеншна audit-логов (обычно `90..365`)
- `OPS_ALERT_ON_REVIEW_THRESHOLD` — порог размера очереди `on_review` (обычно `50..200`)
- `OPS_ALERT_OPEN_INCIDENTS_THRESHOLD` — порог открытых инцидентов (обычно `0..5`)
- `OPS_ALERT_ERROR_RATE_PERCENT_THRESHOLD` — порог error-rate API в процентах (обычно `2..10`)
- `OPS_ALERT_MEDIA_PENDING_THRESHOLD` — порог глубины очереди media processing
- `OPS_ALERT_MEDIA_PENDING_AGE_SECONDS_THRESHOLD` — порог возраста самого старого pending-item
- `OPS_ALERT_MEDIA_FAILED_THRESHOLD` — порог числа failed media-item
- `OPS_ALERT_CACHE_DEGRADED_STORES_THRESHOLD` — порог числа degraded Redis cache stores
- `HEALTH_DEPENDENCY_TIMEOUT_MS` — timeout dependency-check'ов (`/api/health/ready`, `/api/health/deps`)
- `MEDIA_MAX_UPLOAD_BYTES` — максимальный размер загружаемого файла (обычно `5..20 MB`)
- `MEDIA_MAX_IMAGE_DIMENSION` — верхняя граница по длинной стороне изображения (обычно `1920..3072`)
- `MEDIA_MAX_IMAGE_PIXELS` — лимит суммарных пикселей изображения (обычно `12..36 MP`)
- `MEDIA_THUMBNAIL_SIZE` — размер thumbnail по длинной стороне (обычно `256..512`)
- `MEDIA_ASYNC_PROCESSING_ENABLED` — включает асинхронный media pipeline
- `MEDIA_PROCESSING_BATCH_SIZE` — размер batch для media worker/admin trigger
- `MEDIA_PROCESSING_MAX_ATTEMPTS` — max retry попыток media pipeline
- `MEDIA_PROCESSING_RETRY_BACKOFF_SECONDS` — базовый backoff для retry
- `YMAPS_CONFIG_CACHE_TTL_SECONDS` — TTL ответа `/api/config/ymaps` (обычно `600..3600`)
- Для list-эндпоинтов, где UI не показывает общее количество, передавать `include_total=false`
  (`/api/species`, `/api/observations`, `/api/observations/my`, `/api/validation/queue`, `/api/notifications`) чтобы избежать лишнего `COUNT(*)`.
- `UVICORN_WORKERS` — подобрать под CPU (обычно `2..4`)
- `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` — подобрать под число workers и профиль нагрузки

---

## Структура проекта

```
green-book-nlmk/
├── docker-compose.yml          # Оркестрация сервисов
├── docker-compose.perf.yml     # Production-like perf override профиль
├── docker-compose.rehearsal.yml # Изолированные support-сервисы для deploy rehearsal
├── docker-compose.staging.yml  # Image-based compose для staging deploy
├── scripts/                    # Операционные скрипты (backup/restore/maintenance)
├── .env.example                # Шаблон переменных окружения
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── migrations/             # Alembic миграции
│   └── app/
│       ├── main.py             # FastAPI приложение
│       ├── config.py           # Настройки
│       ├── database.py         # SQLAlchemy engine
│       ├── auth.py             # JWT + RBAC
│       ├── models/             # SQLAlchemy модели
│       ├── schemas/            # Pydantic схемы
│       ├── routers/            # API-роутеры
│       ├── services/           # Бизнес-логика (media, geo, gamification)
│       ├── seed/               # Начальные данные
│       └── tests/
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── main.ts
│       ├── App.vue
│       ├── assets/main.css     # Глобальные стили
│       ├── router/             # Vue Router (17 маршрутов)
│       ├── stores/             # Pinia (auth)
│       ├── api/                # Axios клиент
│       ├── components/         # SpeciesCard
│       ├── layouts/            # MainLayout
│       └── views/              # 17 страниц
└── docs/
    ├── screenshots/            # Скриншоты (17 экранов)
    └── superpowers/            # Спецификации и планы
```

---

## Источники данных

Проект основан на материалах:
- **Зелёная книга ПАО «НЛМК»** (2026) — каталог видов, 32 стр.
- **Атлас растительного и животного мира ПАО НЛМК** (2025) — предыдущая версия
- **Проект технического задания для интеграции на портал** — функциональные требования

---

## Лицензия

Внутренний проект ПАО «НЛМК». Все права защищены.
