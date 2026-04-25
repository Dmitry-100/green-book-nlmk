<template>
  <div class="admin-page">
    <h1>Администрирование</h1>

    <div class="admin-tabs">
      <button v-for="t in tabs" :key="t.key" class="admin-tab" :class="{ active: activeTab === t.key }" @click="activeTab = t.key">
        {{ t.icon }} {{ t.label }}
      </button>
    </div>

    <!-- Species Management -->
    <div v-if="activeTab === 'species'" class="admin-section">
      <div class="admin-section__header">
        <h2>Справочник видов</h2>
        <el-button type="primary" size="small" @click="openAddSpecies">+ Добавить вид</el-button>
      </div>

      <div class="catalog-quality" v-loading="catalogQualityLoading">
        <div class="catalog-quality__header">
          <div>
            <h3>Проверка латинских названий</h3>
            <p>Родовые и семейные записи лучше уточнять по первичным источникам.</p>
          </div>
          <div class="catalog-quality__actions">
            <el-button size="small" :loading="catalogExportLoading" @click="downloadCatalogExport(true)">Скачать CSV</el-button>
            <el-button
              size="small"
              :disabled="!adminSpeciesFilters.quality_gap"
              :loading="catalogExportLoading"
              @click="downloadCatalogQualityGapExport"
            >
              CSV очереди
            </el-button>
            <el-button size="small" @click="loadCatalogQuality(true)">Обновить</el-button>
          </div>
        </div>
        <div class="catalog-quality__stats">
          <span>
            <strong>{{ catalogQuality?.latin_name_exact_species ?? 0 }}/{{ catalogQuality?.species_total ?? 0 }}</strong>
            точных
          </span>
          <span>
            <strong>{{ catalogQuality?.latin_name_needs_review ?? 0 }}</strong>
            на проверку
          </span>
          <span :class="{ 'catalog-quality__danger': (catalogQuality?.latin_name_suspicious_chars ?? 0) > 0 }">
            <strong>{{ catalogQuality?.latin_name_suspicious_chars ?? 0 }}</strong>
            с подозрительными символами
          </span>
        </div>
        <div class="catalog-quality__gap-actions">
          <button
            v-for="item in catalogQualityGapItems"
            :key="item.code"
            type="button"
            class="catalog-quality__gap"
            :class="{
              active: adminSpeciesFilters.quality_gap === item.code,
              'catalog-quality__gap--empty': item.count === 0,
            }"
            @click="applyCatalogQualityGap(item.code)"
          >
            <strong>{{ item.count }}</strong>
            {{ item.label.toLowerCase() }}
          </button>
        </div>
        <div v-if="catalogQualityGroups.length" class="catalog-quality__groups">
          <span v-for="item in catalogQualityGroups" :key="item.group">
            {{ groupLabel(item.group) }}: {{ item.total }}
          </span>
        </div>
        <el-table
          v-if="catalogQualityCandidates.length"
          :data="catalogQualityCandidates"
          stripe
          style="width: 100%"
          max-height="260"
          size="small"
        >
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="name_ru" label="Название" min-width="180" />
          <el-table-column prop="name_latin" label="Латынь" min-width="160" />
          <el-table-column prop="group" label="Группа" width="140">
            <template #default="{ row }">{{ groupLabel(row.group) }}</template>
          </el-table-column>
          <el-table-column label="" width="110">
            <template #default="{ row }">
              <router-link class="catalog-quality__link" :to="`/species/${row.id}`">Открыть</router-link>
            </template>
          </el-table-column>
        </el-table>
        <div v-else class="catalog-quality__empty">Нет записей на проверку.</div>

        <div class="catalog-import">
          <div class="catalog-import__header">
            <div>
              <h4>Предпросмотр CSV-правок</h4>
              <p>Файл проверяется без записи в справочник.</p>
            </div>
            <el-upload
              :show-file-list="false"
              accept=".csv"
              :http-request="previewCatalogImport"
            >
              <el-button size="small" :loading="catalogImportLoading">Проверить CSV</el-button>
            </el-upload>
          </div>

          <div v-if="catalogImportPreview" class="catalog-import__preview">
            <div class="catalog-import__stats">
              <span><strong>{{ catalogImportPreview.total_rows }}</strong> строк</span>
              <span><strong>{{ catalogImportPreview.changed_rows }}</strong> с изменениями</span>
              <span><strong>{{ catalogImportPreview.unchanged_rows }}</strong> без изменений</span>
              <span :class="{ 'catalog-quality__danger': catalogImportPreview.error_rows > 0 }">
                <strong>{{ catalogImportPreview.error_rows }}</strong> с ошибками
              </span>
            </div>

            <el-table
              v-if="catalogImportChanges.length"
              :data="catalogImportChanges"
              stripe
              style="width: 100%"
              max-height="220"
              size="small"
            >
              <el-table-column prop="id" label="ID" width="70" />
              <el-table-column prop="name_ru" label="Вид" min-width="160" />
              <el-table-column label="Поля" min-width="160">
                <template #default="{ row }">{{ formatChangedFields(row.changed_fields) }}</template>
              </el-table-column>
              <el-table-column label="Было" min-width="220">
                <template #default="{ row }">{{ formatImportDelta(row.before) }}</template>
              </el-table-column>
              <el-table-column label="Станет" min-width="220">
                <template #default="{ row }">{{ formatImportDelta(row.after) }}</template>
              </el-table-column>
            </el-table>

            <el-table
              v-if="catalogImportErrors.length"
              :data="catalogImportErrors"
              stripe
              style="width: 100%"
              max-height="180"
              size="small"
            >
              <el-table-column prop="row" label="Строка" width="90" />
              <el-table-column prop="id" label="ID" width="90" />
              <el-table-column label="Ошибки" min-width="260">
                <template #default="{ row }">{{ row.errors.join('; ') }}</template>
              </el-table-column>
            </el-table>

            <div v-if="canApplyCatalogImport" class="catalog-import__apply">
              <el-button type="primary" size="small" :loading="catalogApplyLoading" @click="applyCatalogImport">
                Применить CSV
              </el-button>
              <span>Будет обновлено {{ catalogImportPreview.changed_rows }} строк.</span>
            </div>
          </div>

          <div class="catalog-import__history" v-loading="catalogBatchLoading">
            <div class="catalog-import__history-header">
              <h4>История CSV-импортов</h4>
              <div class="catalog-import__history-actions">
                <el-select
                  v-model="catalogBatchStatusFilter"
                  size="small"
                  style="width: 150px"
                  @change="onCatalogBatchStatusChange"
                >
                  <el-option label="Все статусы" value="" />
                  <el-option label="Примененные" value="applied" />
                  <el-option label="Откатанные" value="rolled_back" />
                </el-select>
                <el-button size="small" @click="loadCatalogImportBatches(true)">Обновить</el-button>
              </div>
            </div>
            <el-table
              v-if="catalogImportBatches.length"
              :data="catalogImportBatches"
              stripe
              style="width: 100%"
              max-height="220"
              size="small"
            >
              <el-table-column prop="id" label="Batch" width="80" />
              <el-table-column prop="filename" label="Файл" min-width="160" />
              <el-table-column prop="created_at" label="Дата" width="160">
                <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
              </el-table-column>
              <el-table-column prop="status" label="Статус" width="120">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.status === 'applied' ? 'warning' : 'info'">
                    {{ batchStatusLabel(row.status) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="changed_rows" label="Изменений" width="110" />
              <el-table-column label="" width="170">
                <template #default="{ row }">
                  <el-button
                    size="small"
                    text
                    :loading="catalogBatchDetailLoading === row.id"
                    @click="loadCatalogImportBatchDetail(row.id)"
                  >
                    Детали
                  </el-button>
                  <el-button
                    v-if="row.status === 'applied'"
                    type="danger"
                    size="small"
                    text
                    :loading="catalogRollbackLoading === row.id"
                    @click="rollbackCatalogImportBatch(row)"
                  >
                    Откатить
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
            <div v-else class="catalog-quality__empty">Импортов пока нет.</div>
            <div v-if="catalogBatchTotal > catalogBatchPageSize" class="catalog-import__pagination">
              <el-pagination
                background
                layout="prev, pager, next, total"
                :current-page="catalogBatchPage"
                :page-size="catalogBatchPageSize"
                :total="catalogBatchTotal"
                @current-change="onCatalogBatchPageChange"
              />
            </div>
            <div v-if="catalogBatchDetails" class="catalog-import__details">
              <div class="catalog-import__details-title">
                Batch #{{ catalogBatchDetails.id }}: {{ catalogBatchDetails.filename }}
              </div>
              <el-table
                :data="catalogBatchDetails.changes"
                stripe
                style="width: 100%"
                max-height="220"
                size="small"
              >
                <el-table-column prop="id" label="ID" width="70" />
                <el-table-column prop="name_ru" label="Вид" min-width="160" />
                <el-table-column label="Поля" min-width="160">
                  <template #default="{ row }">{{ formatChangedFields(row.changed_fields) }}</template>
                </el-table-column>
                <el-table-column label="Было" min-width="220">
                  <template #default="{ row }">{{ formatImportDelta(row.before) }}</template>
                </el-table-column>
                <el-table-column label="Стало" min-width="220">
                  <template #default="{ row }">{{ formatImportDelta(row.after) }}</template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </div>
      </div>

      <div class="admin-species-filters">
        <el-input
          v-model="adminSpeciesFilters.search"
          placeholder="Поиск по названию или латыни"
          clearable
          size="small"
          @input="debouncedFetchSpecies"
          @clear="applyAdminSpeciesFilters"
        />
        <el-select
          v-model="adminSpeciesFilters.group"
          placeholder="Группа"
          clearable
          size="small"
          @change="applyAdminSpeciesFilters"
        >
          <el-option label="Растения" value="plants" />
          <el-option label="Грибы" value="fungi" />
          <el-option label="Насекомые" value="insects" />
          <el-option label="Герпетофауна" value="herpetofauna" />
          <el-option label="Птицы" value="birds" />
          <el-option label="Млекопитающие" value="mammals" />
        </el-select>
        <el-select
          v-model="adminSpeciesFilters.category"
          placeholder="Категория"
          clearable
          size="small"
          @change="applyAdminSpeciesFilters"
        >
          <el-option label="Рудеральный" value="ruderal" />
          <el-option label="Типичный" value="typical" />
          <el-option label="Редкий" value="rare" />
          <el-option label="Красная книга" value="red_book" />
          <el-option label="Синантроп" value="synanthropic" />
        </el-select>
        <el-select
          v-model="adminSpeciesFilters.quality_gap"
          placeholder="Пробел"
          clearable
          size="small"
          @change="onAdminSpeciesQualityGapChange"
        >
          <el-option label="Без фото" value="missing_photo" />
          <el-option label="Без описания" value="missing_description" />
          <el-option label="Короткое описание" value="short_description" />
          <el-option label="Без аудио" value="missing_audio" />
        </el-select>
        <el-checkbox
          v-model="adminSpeciesFilters.has_audio"
          class="admin-species-filters__checkbox"
          @change="onAdminSpeciesHasAudioChange"
        >
          С голосом
        </el-checkbox>
        <el-button size="small" @click="resetAdminSpeciesFilters">Сбросить</el-button>
        <span class="admin-species-filters__meta">
          Найдено: {{ adminSpeciesTotal }}
          <template v-if="adminSpeciesTotal > adminSpeciesPageSize">, страница {{ adminSpeciesPage }}</template>
        </span>
      </div>

      <el-table :data="speciesList" stripe style="width: 100%" max-height="500">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name_ru" label="Название (RU)" min-width="180" />
        <el-table-column prop="name_latin" label="Латинское" min-width="180" />
        <el-table-column prop="group" label="Группа" width="130">
          <template #default="{ row }">{{ groupLabel(row.group) }}</template>
        </el-table-column>
        <el-table-column prop="category" label="Категория" width="130" />
        <el-table-column prop="is_poisonous" label="Ядовит" width="80">
          <template #default="{ row }">{{ row.is_poisonous ? '⚠️' : '' }}</template>
        </el-table-column>
        <el-table-column label="Пробелы" min-width="180">
          <template #default="{ row }">
            <div class="admin-species-quality">
              <el-tag
                v-for="badge in buildSpeciesAdminQualityBadges(row)"
                :key="badge.code"
                :type="badge.type"
                size="small"
              >
                {{ badge.label }}
              </el-tag>
              <span v-if="buildSpeciesAdminQualityBadges(row).length === 0" class="admin-species-quality__ok">
                заполнено
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="" width="160">
          <template #default="{ row }">
            <el-button type="primary" size="small" text @click="openEditSpecies(row)">Править</el-button>
            <el-button type="danger" size="small" text @click="deleteSpecies(row.id)">✕</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="adminSpeciesTotal > adminSpeciesPageSize" class="admin-species-pagination">
        <el-pagination
          background
          layout="prev, pager, next, total"
          :current-page="adminSpeciesPage"
          :page-size="adminSpeciesPageSize"
          :total="adminSpeciesTotal"
          @current-change="onAdminSpeciesPageChange"
        />
      </div>
    </div>

    <!-- Zone Import -->
    <div v-if="activeTab === 'zones'" class="admin-section">
      <h2>Импорт зон площадки</h2>
      <p class="admin-hint">Загрузите GeoJSON-файл с полигонами зон промплощадки.</p>
      <div class="upload-area">
        <el-upload
          action="/api/admin/zones/import"
          :headers="authHeaders"
          accept=".geojson,.json"
          :on-success="onZoneUploadSuccess"
          :on-error="onZoneUploadError"
          drag
        >
          <div class="upload-content">
            <span style="font-size: 36px">📁</span>
            <p>Перетащите GeoJSON-файл или нажмите для выбора</p>
            <p class="upload-hint">Поддерживаемые форматы: .geojson, .json</p>
          </div>
        </el-upload>
      </div>
      <div v-if="zoneMessage" class="zone-message" :class="{ success: zoneSuccess }">{{ zoneMessage }}</div>
    </div>

    <!-- Users / Roles -->
    <div v-if="activeTab === 'users'" class="admin-section">
      <h2>Управление ролями</h2>
      <p class="admin-hint">Роли назначаются при первом входе через SSO. Здесь можно повысить сотрудника до эколога или администратора.</p>
      <div class="role-info">
        <div class="role-card">
          <h4>Employee</h4>
          <p>Создаёт наблюдения, видит карту и справочник</p>
        </div>
        <div class="role-card">
          <h4>Ecologist</h4>
          <p>Валидирует наблюдения, экспорт данных, управление чувствительностью</p>
        </div>
        <div class="role-card">
          <h4>Admin</h4>
          <p>Управление справочниками, ролями, импорт зон</p>
        </div>
      </div>
    </div>

    <!-- Audit trail -->
    <div v-if="activeTab === 'audit'" class="admin-section">
      <div class="admin-section__header">
        <h2>Журнал действий</h2>
        <div class="audit-header-actions">
          <el-button size="small" :loading="opsLoading || opsAlertsLoading" @click="loadOpsSnapshot(true)">Обновить сводку</el-button>
          <el-button size="small" @click="reloadAudit(true)">Обновить журнал</el-button>
        </div>
      </div>

      <div class="ops-summary" v-loading="opsLoading">
        <div class="ops-card">
          <div class="ops-card__title">Каталог</div>
          <div class="ops-card__value">{{ opsSummary?.catalog?.species_total ?? 0 }}</div>
          <div class="ops-card__hint">видов в справочнике</div>
        </div>
        <div class="ops-card" :class="{ 'ops-card--warning': (opsSummary?.catalog?.latin_name_needs_review ?? 0) > 0 }">
          <div class="ops-card__title">Латынь</div>
          <div class="ops-card__value">
            {{ opsSummary?.catalog?.latin_name_exact_species ?? 0 }}/{{ opsSummary?.catalog?.species_total ?? 0 }}
          </div>
          <div class="ops-card__hint">
            {{ opsSummary?.catalog?.latin_name_needs_review ?? 0 }} требуют уточнения
          </div>
        </div>
        <div class="ops-card">
          <div class="ops-card__title">Очередь</div>
          <div class="ops-card__value">{{ opsSummary?.pipeline?.on_review ?? 0 }}</div>
          <div class="ops-card__hint">на проверке</div>
        </div>
        <div class="ops-card">
          <div class="ops-card__title">Инциденты</div>
          <div class="ops-card__value">{{ opsSummary?.incidents?.open_incidents ?? 0 }}</div>
          <div class="ops-card__hint">открытых</div>
        </div>
        <div class="ops-card">
          <div class="ops-card__title">Аудит 24ч</div>
          <div class="ops-card__value">{{ opsSummary?.audit?.events_last_24h ?? 0 }}</div>
          <div class="ops-card__hint">событий</div>
        </div>
        <div class="ops-card">
          <div class="ops-card__title">Ошибки API</div>
          <div class="ops-card__value">{{ opsSummary?.metrics?.error_rate_percent ?? 0 }}%</div>
          <div class="ops-card__hint">error rate</div>
        </div>
      </div>

      <div class="ops-alerts" v-loading="opsAlertsLoading">
        <div class="ops-alerts__header">
          <span class="ops-alerts__title">Пороговые оповещения</span>
          <el-tag size="small" :type="opsAlertStatus === 'alert' ? 'danger' : 'success'">
            {{ opsAlertStatus === 'alert' ? 'Есть сигналы' : 'Норма' }}
          </el-tag>
        </div>
        <div v-if="opsAlerts.length === 0" class="ops-alerts__empty">
          Активных сигналов нет.
        </div>
        <div v-else class="ops-alerts__list">
          <div v-for="item in opsAlerts" :key="item.code" class="ops-alert-item">
            <div class="ops-alert-item__message">{{ item.message }}</div>
            <div class="ops-alert-item__meta">
              <span class="ops-alert-item__code">{{ item.code }}</span>
              <span class="ops-alert-item__values">факт {{ item.value }} / порог {{ item.threshold }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="audit-filters">
        <el-input
          v-model="auditFilters.action"
          placeholder="action (например, species.create)"
          clearable
          size="small"
        />
        <el-input
          v-model="auditFilters.target_type"
          placeholder="target_type (species, observation...)"
          clearable
          size="small"
        />
        <el-input
          v-model="auditFilters.actor_user_id"
          placeholder="actor_user_id"
          clearable
          size="small"
        />
        <el-select
          v-model="auditFilters.outcome"
          placeholder="outcome"
          clearable
          size="small"
        >
          <el-option label="success" value="success" />
          <el-option label="noop" value="noop" />
          <el-option label="failed" value="failed" />
        </el-select>
        <el-input
          v-model="auditFilters.request_id"
          placeholder="request_id"
          clearable
          size="small"
        />
      </div>
      <div class="audit-actions">
        <div class="audit-maintenance">
          <span class="audit-maintenance__label">Ретеншн (дни)</span>
          <el-input-number
            v-model="auditRetentionDays"
            :min="1"
            :max="36500"
            size="small"
            controls-position="right"
          />
          <el-button size="small" :loading="auditPurgeLoading" @click="previewAuditPurge">
            Проверить очистку
          </el-button>
          <el-button type="danger" size="small" :loading="auditPurgeLoading" @click="confirmAndPurgeAudit">
            Очистить старые
          </el-button>
        </div>
        <el-button size="small" @click="resetAuditFilters">Сбросить фильтры</el-button>
        <el-button type="primary" size="small" :loading="auditLoading" @click="applyAuditFilters">Применить</el-button>
      </div>

      <el-table :data="auditEvents" stripe style="width: 100%" max-height="520" v-loading="auditLoading">
        <el-table-column prop="created_at" label="Время" width="170">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="action" label="Action" min-width="180" />
        <el-table-column prop="actor_user_id" label="Actor" width="84">
          <template #default="{ row }">
            {{ row.actor_user_id ?? '—' }}
          </template>
        </el-table-column>
        <el-table-column label="Target" min-width="150">
          <template #default="{ row }">
            {{ row.target_type }}#{{ row.target_id ?? '—' }}
          </template>
        </el-table-column>
        <el-table-column prop="outcome" label="Outcome" width="90" />
        <el-table-column prop="details" label="Details" min-width="220">
          <template #default="{ row }">
            <span class="audit-details">{{ formatDetails(row.details) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="request_id" label="Request ID" min-width="140">
          <template #default="{ row }">
            <span class="audit-request-id">{{ row.request_id || '—' }}</span>
          </template>
        </el-table-column>
      </el-table>

      <div class="audit-pagination">
        <el-pagination
          background
          layout="prev, pager, next, total"
          :current-page="auditPage"
          :page-size="auditPageSize"
          :total="auditTotal"
          @current-change="onAuditPageChange"
        />
      </div>
    </div>

    <!-- Add Species Dialog -->
    <el-dialog
      v-model="showAddSpecies"
      title="Добавить вид"
      width="760px"
      class="species-edit-dialog"
    >
      <el-form label-position="top" class="species-edit-form">
        <el-tabs v-model="addSpeciesFormTab" class="species-edit-tabs">
          <el-tab-pane :label="speciesFormTabs[0].label" :name="speciesFormTabs[0].name">
            <div class="species-edit-form__grid">
              <el-form-item label="Название (RU)">
                <el-input v-model="newSpecies.name_ru" />
              </el-form-item>
              <el-form-item label="Латинское название">
                <el-input v-model="newSpecies.name_latin" />
              </el-form-item>
              <el-form-item label="Группа">
                <el-select v-model="newSpecies.group" style="width: 100%">
                  <el-option label="Растения" value="plants" />
                  <el-option label="Грибы" value="fungi" />
                  <el-option label="Насекомые" value="insects" />
                  <el-option label="Герпетофауна" value="herpetofauna" />
                  <el-option label="Птицы" value="birds" />
                  <el-option label="Млекопитающие" value="mammals" />
                </el-select>
              </el-form-item>
              <el-form-item label="Категория">
                <el-select v-model="newSpecies.category" style="width: 100%">
                  <el-option label="Рудеральный" value="ruderal" />
                  <el-option label="Типичный" value="typical" />
                  <el-option label="Редкий" value="rare" />
                  <el-option label="Красная книга" value="red_book" />
                  <el-option label="Синантроп" value="synanthropic" />
                </el-select>
              </el-form-item>
            </div>
            <el-form-item label="Охранный статус">
              <el-input v-model="newSpecies.conservation_status" />
            </el-form-item>
            <el-form-item label="Ядовит">
              <el-checkbox v-model="newSpecies.is_poisonous" />
            </el-form-item>
          </el-tab-pane>

          <el-tab-pane :label="speciesFormTabs[1].label" :name="speciesFormTabs[1].name">
            <el-form-item label="Сезонность">
              <el-input v-model="newSpecies.season_info" />
            </el-form-item>
            <el-form-item label="Местообитания">
              <el-input v-model="newSpecies.biotopes" type="textarea" :rows="2" />
            </el-form-item>
            <el-form-item label="Описание">
              <el-input v-model="newSpecies.description" type="textarea" :rows="4" />
            </el-form-item>
            <el-form-item label="Памятка">
              <el-input v-model="newSpecies.do_dont_rules" type="textarea" :rows="3" />
            </el-form-item>
          </el-tab-pane>

          <el-tab-pane :label="speciesFormTabs[2].label" :name="speciesFormTabs[2].name">
            <el-form-item label="Фото, по одному URL на строку">
              <el-input v-model="newSpecies.photo_urls_text" type="textarea" :rows="3" />
            </el-form-item>
            <div class="species-edit-form__grid">
              <el-form-item label="Аудио URL">
                <el-input v-model="newSpecies.audio_url" />
              </el-form-item>
              <el-form-item label="Название аудио">
                <el-input v-model="newSpecies.audio_title" />
              </el-form-item>
              <el-form-item label="Источник аудио">
                <el-input v-model="newSpecies.audio_source" />
              </el-form-item>
              <el-form-item label="Лицензия аудио">
                <el-input v-model="newSpecies.audio_license" />
              </el-form-item>
            </div>
          </el-tab-pane>
        </el-tabs>
        <div class="species-form-preview">
          <div
            class="species-form-preview__image"
            :style="addSpeciesPreview.photo_url ? { backgroundImage: `url(${addSpeciesPreview.photo_url})` } : {}"
          >
            <span v-if="!addSpeciesPreview.photo_url">{{ groupIcon(addSpeciesPreview.group) }}</span>
          </div>
          <div class="species-form-preview__body">
            <div class="species-form-preview__eyebrow">Предпросмотр карточки</div>
            <h3>{{ addSpeciesPreview.name_ru || 'Название вида' }}</h3>
            <div class="species-form-preview__latin">{{ addSpeciesPreview.name_latin || 'Latin name' }}</div>
            <div class="species-form-preview__tags">
              <span>{{ groupLabel(addSpeciesPreview.group) }}</span>
              <span>{{ categoryLabel(addSpeciesPreview.category) }}</span>
              <span v-if="addSpeciesPreview.conservation_status">{{ addSpeciesPreview.conservation_status }}</span>
              <span v-if="addSpeciesPreview.has_audio">Есть голос</span>
              <span v-if="addSpeciesPreview.is_poisonous">Ядовит</span>
            </div>
            <p v-if="addSpeciesPreview.description">{{ addSpeciesPreview.description }}</p>
            <div class="species-form-preview__facts">
              <span v-if="addSpeciesPreview.season_info">Когда: {{ addSpeciesPreview.season_info }}</span>
              <span v-if="addSpeciesPreview.biotopes">Где: {{ addSpeciesPreview.biotopes }}</span>
              <span v-if="addSpeciesPreview.do_dont_rules">Памятка: {{ addSpeciesPreview.do_dont_rules }}</span>
              <span v-if="addSpeciesPreview.audio_title">Аудио: {{ addSpeciesPreview.audio_title }}</span>
            </div>
          </div>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="showAddSpecies = false">Отмена</el-button>
        <el-button type="primary" @click="addSpecies">Добавить</el-button>
      </template>
    </el-dialog>

    <!-- Edit Species Dialog -->
    <el-dialog
      v-model="showEditSpecies"
      title="Редактировать вид"
      width="760px"
      class="species-edit-dialog"
    >
      <el-form v-if="editSpeciesForm" label-position="top" class="species-edit-form">
        <el-tabs v-model="editSpeciesFormTab" class="species-edit-tabs">
          <el-tab-pane :label="speciesFormTabs[0].label" :name="speciesFormTabs[0].name">
            <div class="species-edit-form__grid">
              <el-form-item label="Название (RU)">
                <el-input v-model="editSpeciesForm.name_ru" />
              </el-form-item>
              <el-form-item label="Латинское название">
                <el-input v-model="editSpeciesForm.name_latin" />
              </el-form-item>
              <el-form-item label="Группа">
                <el-select v-model="editSpeciesForm.group" style="width: 100%">
                  <el-option label="Растения" value="plants" />
                  <el-option label="Грибы" value="fungi" />
                  <el-option label="Насекомые" value="insects" />
                  <el-option label="Герпетофауна" value="herpetofauna" />
                  <el-option label="Птицы" value="birds" />
                  <el-option label="Млекопитающие" value="mammals" />
                </el-select>
              </el-form-item>
              <el-form-item label="Категория">
                <el-select v-model="editSpeciesForm.category" style="width: 100%">
                  <el-option label="Рудеральный" value="ruderal" />
                  <el-option label="Типичный" value="typical" />
                  <el-option label="Редкий" value="rare" />
                  <el-option label="Красная книга" value="red_book" />
                  <el-option label="Синантроп" value="synanthropic" />
                </el-select>
              </el-form-item>
            </div>
            <el-form-item label="Охранный статус">
              <el-input v-model="editSpeciesForm.conservation_status" />
            </el-form-item>
            <el-form-item label="Ядовит">
              <el-checkbox v-model="editSpeciesForm.is_poisonous" />
            </el-form-item>
          </el-tab-pane>

          <el-tab-pane :label="speciesFormTabs[1].label" :name="speciesFormTabs[1].name">
            <el-form-item label="Сезонность">
              <el-input v-model="editSpeciesForm.season_info" />
            </el-form-item>
            <el-form-item label="Местообитания">
              <el-input v-model="editSpeciesForm.biotopes" type="textarea" :rows="2" />
            </el-form-item>
            <el-form-item label="Описание">
              <el-input v-model="editSpeciesForm.description" type="textarea" :rows="4" />
            </el-form-item>
            <el-form-item label="Памятка">
              <el-input v-model="editSpeciesForm.do_dont_rules" type="textarea" :rows="3" />
            </el-form-item>
          </el-tab-pane>

          <el-tab-pane :label="speciesFormTabs[2].label" :name="speciesFormTabs[2].name">
            <el-form-item label="Фото, по одному URL на строку">
              <el-input v-model="editSpeciesForm.photo_urls_text" type="textarea" :rows="3" />
            </el-form-item>
            <div class="species-edit-form__grid">
              <el-form-item label="Аудио URL">
                <el-input v-model="editSpeciesForm.audio_url" />
              </el-form-item>
              <el-form-item label="Название аудио">
                <el-input v-model="editSpeciesForm.audio_title" />
              </el-form-item>
              <el-form-item label="Источник аудио">
                <el-input v-model="editSpeciesForm.audio_source" />
              </el-form-item>
              <el-form-item label="Лицензия аудио">
                <el-input v-model="editSpeciesForm.audio_license" />
              </el-form-item>
            </div>
          </el-tab-pane>
        </el-tabs>
        <div v-if="editSpeciesPreview" class="species-form-preview">
          <div
            class="species-form-preview__image"
            :style="editSpeciesPreview.photo_url ? { backgroundImage: `url(${editSpeciesPreview.photo_url})` } : {}"
          >
            <span v-if="!editSpeciesPreview.photo_url">{{ groupIcon(editSpeciesPreview.group) }}</span>
          </div>
          <div class="species-form-preview__body">
            <div class="species-form-preview__eyebrow">Предпросмотр карточки</div>
            <h3>{{ editSpeciesPreview.name_ru || 'Название вида' }}</h3>
            <div class="species-form-preview__latin">{{ editSpeciesPreview.name_latin || 'Latin name' }}</div>
            <div class="species-form-preview__tags">
              <span>{{ groupLabel(editSpeciesPreview.group) }}</span>
              <span>{{ categoryLabel(editSpeciesPreview.category) }}</span>
              <span v-if="editSpeciesPreview.conservation_status">{{ editSpeciesPreview.conservation_status }}</span>
              <span v-if="editSpeciesPreview.has_audio">Есть голос</span>
              <span v-if="editSpeciesPreview.is_poisonous">Ядовит</span>
            </div>
            <p v-if="editSpeciesPreview.description">{{ editSpeciesPreview.description }}</p>
            <div class="species-form-preview__facts">
              <span v-if="editSpeciesPreview.season_info">Когда: {{ editSpeciesPreview.season_info }}</span>
              <span v-if="editSpeciesPreview.biotopes">Где: {{ editSpeciesPreview.biotopes }}</span>
              <span v-if="editSpeciesPreview.do_dont_rules">Памятка: {{ editSpeciesPreview.do_dont_rules }}</span>
              <span v-if="editSpeciesPreview.audio_title">Аудио: {{ editSpeciesPreview.audio_title }}</span>
            </div>
          </div>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="showEditSpecies = false">Отмена</el-button>
        <el-button type="primary" :loading="editSpeciesSaving" @click="saveSpeciesEdit">Сохранить</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api, { clearCachedGets, getCached } from '../api/client'
import { useAuthStore } from '../stores/auth'
import {
  formatCatalogImportDelta,
  formatCatalogImportFields,
} from '../utils/catalogImportFormatting'
import {
  SPECIES_ADMIN_FORM_TABS,
  buildAdminSpeciesListCacheKey,
  buildAdminSpeciesListParams,
  buildAdminSpeciesListUrlQuery,
  buildSpeciesAdminQualityGapExportFilename,
  buildSpeciesAdminQualityGapItems,
  buildSpeciesAdminQualityBadges,
  buildEmptySpeciesForm,
  clampAdminSpeciesListPage,
  parseAdminSpeciesListUrlState,
  buildSpeciesEditForm,
  buildSpeciesFormPreview,
  buildSpeciesUpdatePayload,
  type AdminSpeciesListFilters,
  type AdminSpeciesQualityGap,
  type SpeciesContentGapCounts,
  type AdminSpeciesEditForm,
  type AdminSpeciesRow,
} from '../utils/speciesAdminForm'

type AuditEvent = {
  id: number
  created_at: string
  action: string
  actor_user_id: number | null
  actor_role: string | null
  target_type: string
  target_id: number | null
  outcome: string
  details: Record<string, unknown>
  request_id: string | null
}

type OpsAlert = {
  code: string
  severity: string
  message: string
  value: number
  threshold: number
}

type CatalogQualityItem = {
  id: number
  name_ru: string
  name_latin: string
  group: string
}

type CatalogQuality = {
  generated_at: string
  species_total: number
  latin_name_exact_species: number
  latin_name_needs_review: number
  latin_name_suspicious_chars: number
  latin_name_needs_review_by_group: Record<string, number>
  latin_name_needs_review_examples: CatalogQualityItem[]
  content_gap_counts: SpeciesContentGapCounts
}

type CatalogImportChange = {
  row: number
  id: number
  name_ru: string
  changed_fields: string[]
  before: Record<string, unknown>
  after: Record<string, unknown>
}

type CatalogImportRowError = {
  row: number
  id: string
  errors: string[]
}

type CatalogImportPreview = {
  filename: string
  dry_run: boolean
  batch_id?: number
  total_rows: number
  changed_rows: number
  unchanged_rows: number
  error_rows: number
  applied_rows?: number
  changes: CatalogImportChange[]
  errors: CatalogImportRowError[]
}

type CatalogImportBatch = {
  id: number
  filename: string
  status: 'applied' | 'rolled_back'
  actor_user_id: number | null
  rolled_back_by_user_id: number | null
  total_rows: number
  changed_rows: number
  unchanged_rows: number
  error_rows: number
  applied_rows: number
  created_at: string
  rolled_back_at: string | null
}

type CatalogImportBatchDetail = CatalogImportBatch & {
  changes: CatalogImportChange[]
}

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const activeTab = ref('species')
const speciesList = ref<any[]>([])
const adminSpeciesTotal = ref(0)
const adminSpeciesPage = ref(1)
const adminSpeciesPageSize = 50
const adminSpeciesFilters = reactive<AdminSpeciesListFilters>({
  search: '',
  group: '',
  category: '',
  has_audio: false,
  quality_gap: '',
})
const catalogQuality = ref<CatalogQuality | null>(null)
const catalogQualityLoading = ref(false)
const catalogExportLoading = ref(false)
const catalogImportPreview = ref<CatalogImportPreview | null>(null)
const catalogImportLoading = ref(false)
const catalogApplyLoading = ref(false)
const catalogImportFile = ref<File | null>(null)
const catalogImportBatches = ref<CatalogImportBatch[]>([])
const catalogBatchDetails = ref<CatalogImportBatchDetail | null>(null)
const catalogBatchLoading = ref(false)
const catalogBatchDetailLoading = ref<number | null>(null)
const catalogRollbackLoading = ref<number | null>(null)
const catalogBatchStatusFilter = ref('')
const catalogBatchPage = ref(1)
const catalogBatchPageSize = 5
const catalogBatchTotal = ref(0)
const showAddSpecies = ref(false)
const showEditSpecies = ref(false)
const editSpeciesSaving = ref(false)
const editSpeciesForm = ref<AdminSpeciesEditForm | null>(null)
const speciesFormTabs = SPECIES_ADMIN_FORM_TABS
const addSpeciesFormTab = ref(SPECIES_ADMIN_FORM_TABS[0].name)
const editSpeciesFormTab = ref(SPECIES_ADMIN_FORM_TABS[0].name)
const zoneMessage = ref('')
const zoneSuccess = ref(false)
const auditEvents = ref<AuditEvent[]>([])
const auditLoading = ref(false)
const auditPurgeLoading = ref(false)
const auditRetentionDays = ref(180)
const auditPage = ref(1)
const auditPageSize = 20
const auditTotal = ref(0)
const opsSummary = ref<any | null>(null)
const opsLoading = ref(false)
const opsAlerts = ref<OpsAlert[]>([])
const opsAlertsLoading = ref(false)
const opsAlertStatus = ref<'ok' | 'alert'>('ok')
const auditFilters = reactive({
  action: '',
  target_type: '',
  actor_user_id: '',
  outcome: '',
  request_id: '',
})

const tabs = [
  { key: 'species', icon: '📋', label: 'Виды' },
  { key: 'zones', icon: '🗺️', label: 'Зоны' },
  { key: 'users', icon: '👤', label: 'Роли' },
  { key: 'audit', icon: '🧾', label: 'Аудит' },
]

const GROUP_LABELS: Record<string, string> = { plants: 'Растения', fungi: 'Грибы', insects: 'Насекомые', herpetofauna: 'Герпетофауна', birds: 'Птицы', mammals: 'Млекопитающие' }
function groupLabel(g: string) { return GROUP_LABELS[g] || g }
const GROUP_ICONS: Record<string, string> = { plants: '🌿', fungi: '🍄', insects: '🐛', herpetofauna: '🐍', birds: '🐦', mammals: '🦔' }
const CATEGORY_LABELS: Record<string, string> = { ruderal: 'Рудеральный', typical: 'Типичный', rare: 'Редкий', red_book: 'Красная книга', synanthropic: 'Синантроп' }
function groupIcon(g: string) { return GROUP_ICONS[g] || '🌱' }
function categoryLabel(category: string) { return CATEGORY_LABELS[category] || category }

const catalogQualityCandidates = computed(
  () => catalogQuality.value?.latin_name_needs_review_examples || []
)
const catalogQualityGroups = computed(() => Object.entries(
  catalogQuality.value?.latin_name_needs_review_by_group || {}
).map(([group, total]) => ({ group, total })))
const catalogQualityGapItems = computed(() =>
  buildSpeciesAdminQualityGapItems(catalogQuality.value?.content_gap_counts)
)
const catalogImportChanges = computed(() => catalogImportPreview.value?.changes || [])
const catalogImportErrors = computed(() => catalogImportPreview.value?.errors || [])
const canApplyCatalogImport = computed(() => {
  const preview = catalogImportPreview.value
  return Boolean(preview && preview.error_rows === 0 && preview.changed_rows > 0)
})
const addSpeciesPreview = computed(() => buildSpeciesFormPreview(newSpecies))
const editSpeciesPreview = computed(() =>
  editSpeciesForm.value ? buildSpeciesFormPreview(editSpeciesForm.value) : null
)

const authHeaders = { Authorization: `Bearer ${auth.token || ''}` }

const newSpecies = reactive<AdminSpeciesEditForm>(buildEmptySpeciesForm())
let adminSpeciesSearchTimer: ReturnType<typeof setTimeout>

function adminSpeciesPagination() {
  return {
    page: adminSpeciesPage.value,
    pageSize: adminSpeciesPageSize,
  }
}

function adminSpeciesUrlStateSignature(
  filters: AdminSpeciesListFilters,
  pagination: { page: number; pageSize: number }
) {
  return JSON.stringify({ filters, pagination })
}

function applyAdminSpeciesStateFromUrl(): boolean {
  const { filters, pagination } = parseAdminSpeciesListUrlState(
    route.query,
    adminSpeciesPageSize
  )
  const currentSignature = adminSpeciesUrlStateSignature(
    { ...adminSpeciesFilters },
    adminSpeciesPagination()
  )
  const nextSignature = adminSpeciesUrlStateSignature(filters, pagination)
  if (currentSignature === nextSignature) {
    return false
  }

  Object.assign(adminSpeciesFilters, filters)
  adminSpeciesPage.value = pagination.page
  return true
}

function syncAdminSpeciesUrl() {
  router.replace({
    query: buildAdminSpeciesListUrlQuery(
      route.query,
      adminSpeciesFilters,
      adminSpeciesPagination()
    ),
  })
}

async function fetchSpecies(force = false) {
  const params = buildAdminSpeciesListParams(adminSpeciesFilters, {
    page: adminSpeciesPage.value,
    pageSize: adminSpeciesPageSize,
  })
  const response = force
    ? await api.get('/species', { params })
    : await getCached(
        '/species',
        { params },
        5 * 60 * 1000,
        buildAdminSpeciesListCacheKey(params)
      )
  const data = response.data
  const total = data.total ?? data.items?.length ?? 0
  const safePage = clampAdminSpeciesListPage(
    adminSpeciesPage.value,
    total,
    adminSpeciesPageSize
  )
  if (safePage !== adminSpeciesPage.value) {
    adminSpeciesPage.value = safePage
    syncAdminSpeciesUrl()
    await fetchSpecies(true)
    return
  }

  speciesList.value = data.items || []
  adminSpeciesTotal.value = total
}

function applyAdminSpeciesFilters() {
  adminSpeciesPage.value = 1
  clearCachedGets('species:list:admin:')
  syncAdminSpeciesUrl()
  fetchSpecies(true)
}

function onAdminSpeciesHasAudioChange() {
  if (adminSpeciesFilters.has_audio && adminSpeciesFilters.quality_gap === 'missing_audio') {
    adminSpeciesFilters.quality_gap = ''
  }
  applyAdminSpeciesFilters()
}

function onAdminSpeciesQualityGapChange() {
  if (adminSpeciesFilters.quality_gap === 'missing_audio') {
    adminSpeciesFilters.has_audio = false
  }
  applyAdminSpeciesFilters()
}

function applyCatalogQualityGap(gap: AdminSpeciesQualityGap) {
  adminSpeciesFilters.quality_gap =
    adminSpeciesFilters.quality_gap === gap ? '' : gap
  if (adminSpeciesFilters.quality_gap === 'missing_audio') {
    adminSpeciesFilters.has_audio = false
  }
  applyAdminSpeciesFilters()
}

function debouncedFetchSpecies() {
  clearTimeout(adminSpeciesSearchTimer)
  adminSpeciesSearchTimer = setTimeout(applyAdminSpeciesFilters, 300)
}

function resetAdminSpeciesFilters() {
  adminSpeciesFilters.search = ''
  adminSpeciesFilters.group = ''
  adminSpeciesFilters.category = ''
  adminSpeciesFilters.has_audio = false
  adminSpeciesFilters.quality_gap = ''
  applyAdminSpeciesFilters()
}

function onAdminSpeciesPageChange(page: number) {
  adminSpeciesPage.value = page
  syncAdminSpeciesUrl()
  fetchSpecies()
}

async function loadCatalogQuality(force = false) {
  catalogQualityLoading.value = true
  const params = { limit: 200 }
  try {
    const response = force
      ? await api.get('/admin/catalog/quality', { params })
      : await getCached(
          '/admin/catalog/quality',
          { params },
          30 * 1000,
          'admin:catalog:quality:200'
        )
    catalogQuality.value = response.data
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || 'Не удалось загрузить проверку каталога')
  } finally {
    catalogQualityLoading.value = false
  }
}

async function loadCatalogImportBatches(force = false) {
  catalogBatchLoading.value = true
  const params: Record<string, string | number> = {
    skip: (catalogBatchPage.value - 1) * catalogBatchPageSize,
    limit: catalogBatchPageSize,
  }
  if (catalogBatchStatusFilter.value) {
    params.status = catalogBatchStatusFilter.value
  }
  const cacheKey = `admin:catalog:import:batches:${JSON.stringify(params)}`
  try {
    const response = force
      ? await api.get('/admin/catalog/import/batches', { params })
      : await getCached(
          '/admin/catalog/import/batches',
          { params },
          10 * 1000,
          cacheKey
        )
    catalogImportBatches.value = response.data.items || []
    catalogBatchTotal.value = response.data.total ?? catalogImportBatches.value.length
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || 'Не удалось загрузить историю импортов')
  } finally {
    catalogBatchLoading.value = false
  }
}

function onCatalogBatchStatusChange() {
  catalogBatchPage.value = 1
  catalogBatchDetails.value = null
  clearCachedGets('admin:catalog:import:batches:')
  loadCatalogImportBatches(true)
}

function onCatalogBatchPageChange(page: number) {
  catalogBatchPage.value = page
  catalogBatchDetails.value = null
  loadCatalogImportBatches()
}

async function loadCatalogImportBatchDetail(batchId: number) {
  catalogBatchDetailLoading.value = batchId
  try {
    const { data } = await api.get(`/admin/catalog/import/batches/${batchId}`)
    catalogBatchDetails.value = data
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || 'Не удалось загрузить детали импорта')
  } finally {
    catalogBatchDetailLoading.value = null
  }
}

function triggerDownload(data: Blob, filename: string) {
  const url = URL.createObjectURL(data)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

async function downloadCatalogExport(needsReview = true) {
  return downloadCatalogExportFile({ needsReview })
}

async function downloadCatalogQualityGapExport() {
  const qualityGap = adminSpeciesFilters.quality_gap
  if (!qualityGap) {
    ElMessage.warning('Выберите очередь')
    return
  }
  return downloadCatalogExportFile({ needsReview: false, qualityGap })
}

async function downloadCatalogExportFile({
  needsReview,
  qualityGap = '',
}: {
  needsReview: boolean
  qualityGap?: AdminSpeciesQualityGap
}) {
  catalogExportLoading.value = true
  try {
    const params: Record<string, string | boolean> = { needs_review: needsReview }
    if (qualityGap) {
      params.quality_gap = qualityGap
    }
    const response = await api.get('/admin/catalog/export', {
      params,
      responseType: 'blob',
    })
    triggerDownload(
      response.data,
      qualityGap
        ? buildSpeciesAdminQualityGapExportFilename(qualityGap)
        : needsReview ? 'species-catalog-needs-review.csv' : 'species-catalog.csv'
    )
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || 'Не удалось скачать каталог')
  } finally {
    catalogExportLoading.value = false
  }
}

function formatChangedFields(fields: string[]): string {
  return formatCatalogImportFields(fields)
}

function formatImportDelta(values: Record<string, unknown>): string {
  return formatCatalogImportDelta(values)
}

async function previewCatalogImport(options: any) {
  catalogImportLoading.value = true
  catalogImportFile.value = options.file
  const formData = new FormData()
  formData.append('file', options.file)
  try {
    const { data } = await api.post('/admin/catalog/import/preview', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    catalogImportPreview.value = data
    options.onSuccess?.(data)
    if (data.error_rows > 0) {
      ElMessage.warning(`Проверка завершена: ошибок ${data.error_rows}`)
      return
    }
    ElMessage.success(`Проверка завершена: изменений ${data.changed_rows}`)
  } catch (e: any) {
    options.onError?.(e)
    ElMessage.error(e.response?.data?.detail || 'Не удалось проверить CSV')
  } finally {
    catalogImportLoading.value = false
  }
}

async function applyCatalogImport() {
  if (!catalogImportFile.value || !catalogImportPreview.value) {
    ElMessage.error('Сначала проверьте CSV')
    return
  }
  if (catalogImportPreview.value.error_rows > 0) {
    ElMessage.error('CSV с ошибками нельзя применить')
    return
  }
  const confirmed = window.confirm(
    `Применить ${catalogImportPreview.value.changed_rows} изменений в справочник?`
  )
  if (!confirmed) {
    return
  }

  catalogApplyLoading.value = true
  const formData = new FormData()
  formData.append('file', catalogImportFile.value)
  try {
    const { data } = await api.post('/admin/catalog/import/apply', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    catalogImportPreview.value = data
    clearCachedGets('species:list:')
    clearCachedGets('admin:audit:')
    clearCachedGets('admin:ops:')
    clearCachedGets('admin:catalog:')
    await Promise.all([
      fetchSpecies(true),
      loadCatalogQuality(true),
      loadCatalogImportBatches(true),
    ])
    ElMessage.success(`Применено строк: ${data.applied_rows}`)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || 'Не удалось применить CSV')
  } finally {
    catalogApplyLoading.value = false
  }
}

function batchStatusLabel(status: string): string {
  if (status === 'applied') return 'Применен'
  if (status === 'rolled_back') return 'Откатан'
  return status
}

async function rollbackCatalogImportBatch(batch: CatalogImportBatch) {
  const confirmed = window.confirm(`Откатить CSV-импорт #${batch.id}?`)
  if (!confirmed) {
    return
  }
  catalogRollbackLoading.value = batch.id
  try {
    const { data } = await api.post(`/admin/catalog/import/batches/${batch.id}/rollback`)
    clearCachedGets('species:list:')
    clearCachedGets('admin:audit:')
    clearCachedGets('admin:ops:')
    clearCachedGets('admin:catalog:')
    await Promise.all([
      fetchSpecies(true),
      loadCatalogQuality(true),
      loadCatalogImportBatches(true),
    ])
    ElMessage.success(`Откатили строк: ${data.rolled_back_rows}`)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || 'Не удалось откатить импорт')
  } finally {
    catalogRollbackLoading.value = null
  }
}

async function addSpecies() {
  try {
    await api.post('/species', buildSpeciesUpdatePayload(newSpecies))
    showAddSpecies.value = false
    Object.assign(newSpecies, buildEmptySpeciesForm())
    addSpeciesFormTab.value = SPECIES_ADMIN_FORM_TABS[0].name
    ElMessage.success('Вид добавлен')
    clearCachedGets('species:list:')
    clearCachedGets('admin:audit:')
    clearCachedGets('admin:ops:')
    clearCachedGets('admin:catalog:')
    fetchSpecies(true)
    loadCatalogQuality(true)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || 'Ошибка')
  }
}

function openAddSpecies() {
  Object.assign(newSpecies, buildEmptySpeciesForm())
  addSpeciesFormTab.value = SPECIES_ADMIN_FORM_TABS[0].name
  showAddSpecies.value = true
}

function openEditSpecies(row: AdminSpeciesRow) {
  editSpeciesForm.value = buildSpeciesEditForm(row)
  editSpeciesFormTab.value = SPECIES_ADMIN_FORM_TABS[0].name
  showEditSpecies.value = true
}

async function saveSpeciesEdit() {
  if (!editSpeciesForm.value) {
    return
  }
  editSpeciesSaving.value = true
  try {
    await api.put(
      `/species/${editSpeciesForm.value.id}`,
      buildSpeciesUpdatePayload(editSpeciesForm.value)
    )
    showEditSpecies.value = false
    editSpeciesForm.value = null
    ElMessage.success('Вид обновлён')
    clearCachedGets('species:list:')
    clearCachedGets('admin:audit:')
    clearCachedGets('admin:ops:')
    clearCachedGets('admin:catalog:')
    await Promise.all([
      fetchSpecies(true),
      loadCatalogQuality(true),
    ])
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || 'Не удалось обновить вид')
  } finally {
    editSpeciesSaving.value = false
  }
}

async function deleteSpecies(id: number) {
  try {
    await api.delete(`/species/${id}`)
    ElMessage.success('Вид удалён')
    clearCachedGets('species:list:')
    clearCachedGets('admin:audit:')
    clearCachedGets('admin:ops:')
    clearCachedGets('admin:catalog:')
    fetchSpecies(true)
    loadCatalogQuality(true)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || 'Ошибка')
  }
}

function buildAuditParams(): Record<string, string | number | boolean> {
  const params: Record<string, string | number | boolean> = {
    skip: (auditPage.value - 1) * auditPageSize,
    limit: auditPageSize,
    include_total: true,
  }
  const action = auditFilters.action.trim()
  if (action) {
    params.action = action
  }
  const targetType = auditFilters.target_type.trim()
  if (targetType) {
    params.target_type = targetType
  }
  const outcome = auditFilters.outcome.trim()
  if (outcome) {
    params.outcome = outcome
  }
  const requestId = auditFilters.request_id.trim()
  if (requestId) {
    params.request_id = requestId
  }
  const actorUserId = Number.parseInt(auditFilters.actor_user_id.trim(), 10)
  if (Number.isInteger(actorUserId) && actorUserId > 0) {
    params.actor_user_id = actorUserId
  }
  return params
}

function buildAuditCacheKey(params: Record<string, string | number | boolean>): string {
  const safe = {
    action: params.action || '',
    target_type: params.target_type || '',
    actor_user_id: params.actor_user_id || '',
    outcome: params.outcome || '',
    request_id: params.request_id || '',
    skip: params.skip,
    limit: params.limit,
  }
  return `admin:audit:${JSON.stringify(safe)}`
}

async function reloadAudit(force = false) {
  auditLoading.value = true
  const params = buildAuditParams()
  try {
    const response = force
      ? await api.get('/admin/audit/events', { params })
      : await getCached(
          '/admin/audit/events',
          { params },
          10 * 1000,
          buildAuditCacheKey(params)
        )
    auditEvents.value = response.data.items || []
    auditTotal.value = response.data.total ?? auditEvents.value.length
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || 'Не удалось загрузить журнал аудита')
  } finally {
    auditLoading.value = false
  }
}

async function loadOpsSummary(force = false) {
  opsLoading.value = true
  try {
    const response = force
      ? await api.get('/admin/ops/summary')
      : await getCached(
          '/admin/ops/summary',
          {},
          10 * 1000,
          'admin:ops:summary'
        )
    opsSummary.value = response.data
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || 'Не удалось загрузить операционную сводку')
  } finally {
    opsLoading.value = false
  }
}

async function loadOpsAlerts(force = false) {
  opsAlertsLoading.value = true
  try {
    const response = force
      ? await api.get('/admin/ops/alerts')
      : await getCached(
          '/admin/ops/alerts',
          {},
          10 * 1000,
          'admin:ops:alerts'
        )
    opsAlertStatus.value = response.data.status === 'alert' ? 'alert' : 'ok'
    opsAlerts.value = response.data.alerts || []
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || 'Не удалось загрузить пороговые оповещения')
  } finally {
    opsAlertsLoading.value = false
  }
}

async function loadOpsSnapshot(force = false) {
  await Promise.all([loadOpsSummary(force), loadOpsAlerts(force)])
}

async function runAuditPurge(dryRun: boolean) {
  auditPurgeLoading.value = true
  try {
    const { data } = await api.post(
      '/admin/audit/purge',
      null,
      {
        params: {
          older_than_days: auditRetentionDays.value,
          dry_run: dryRun,
        },
      }
    )
    if (dryRun) {
      ElMessage.info(`Кандидатов на удаление: ${data.candidates}`)
      return
    }
    ElMessage.success(`Удалено записей: ${data.deleted}`)
    clearCachedGets('admin:audit:')
    clearCachedGets('admin:ops:')
    loadOpsSnapshot(true)
    reloadAudit(true)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || 'Не удалось очистить audit logs')
  } finally {
    auditPurgeLoading.value = false
  }
}

function previewAuditPurge() {
  runAuditPurge(true)
}

function confirmAndPurgeAudit() {
  const confirmed = window.confirm(
    `Удалить audit-события старше ${auditRetentionDays.value} дней?`
  )
  if (!confirmed) {
    return
  }
  runAuditPurge(false)
}

function applyAuditFilters() {
  auditPage.value = 1
  clearCachedGets('admin:audit:')
  reloadAudit(true)
}

function resetAuditFilters() {
  auditFilters.action = ''
  auditFilters.target_type = ''
  auditFilters.actor_user_id = ''
  auditFilters.outcome = ''
  auditFilters.request_id = ''
  applyAuditFilters()
}

function onAuditPageChange(page: number) {
  auditPage.value = page
  reloadAudit()
}

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString('ru-RU')
}

function formatDetails(details: Record<string, unknown> | null | undefined): string {
  if (!details || Object.keys(details).length === 0) {
    return '—'
  }
  const payload = JSON.stringify(details)
  if (payload.length <= 120) {
    return payload
  }
  return `${payload.slice(0, 117)}...`
}

function onZoneUploadSuccess(res: any) {
  zoneMessage.value = `Импортировано ${res.imported} зон из ${res.filename}`
  zoneSuccess.value = true
  clearCachedGets('admin:audit:')
  clearCachedGets('admin:ops:')
  if (activeTab.value === 'audit') {
    loadOpsSnapshot(true)
    reloadAudit(true)
  }
}

function onZoneUploadError() {
  zoneMessage.value = 'Ошибка загрузки файла'
  zoneSuccess.value = false
}

watch(activeTab, (tab) => {
  if (tab === 'species') {
    applyAdminSpeciesStateFromUrl()
    fetchSpecies()
    loadCatalogQuality()
    loadCatalogImportBatches()
  }
  if (tab === 'audit') {
    loadOpsSnapshot()
    reloadAudit()
  }
})

watch(
  () => route.query,
  () => {
    if (activeTab.value !== 'species') {
      return
    }
    if (applyAdminSpeciesStateFromUrl()) {
      fetchSpecies(true)
    }
  }
)

onMounted(() => {
  applyAdminSpeciesStateFromUrl()
  fetchSpecies()
  loadCatalogQuality()
  loadCatalogImportBatches()
})
</script>

<style scoped>
.admin-page { max-width: 1000px; margin: 0 auto; padding: 32px; }
.admin-page h1 { font-family: var(--font-display); font-size: 30px; font-weight: 600; color: var(--teal-dark); margin-bottom: 20px; }
.admin-tabs { display: flex; gap: 4px; margin-bottom: 24px; background: var(--slate-bg); border-radius: 12px; padding: 4px; }
.admin-tab { padding: 10px 20px; border: none; background: transparent; font-size: 13px; font-weight: 600; color: var(--slate-mid); cursor: pointer; border-radius: 8px; transition: all 0.2s; }
.admin-tab.active { background: var(--white); color: var(--teal-dark); box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
.admin-section { background: var(--white); border-radius: var(--radius-lg); padding: 28px; box-shadow: var(--shadow-card); }
.admin-section__header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.audit-header-actions { display: flex; gap: 8px; }
.admin-section h2 { font-family: var(--font-display); font-size: 22px; font-weight: 600; color: var(--teal-dark); margin-bottom: 12px; }
.admin-hint { font-size: 14px; color: var(--slate-mid); margin-bottom: 20px; }
.catalog-quality { margin-bottom: 18px; padding-bottom: 18px; border-bottom: 1px solid #D6E0E3; }
.catalog-quality__header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 10px; }
.catalog-quality__header h3 { font-size: 16px; font-weight: 700; color: var(--teal-dark); margin: 0 0 4px; }
.catalog-quality__header p { font-size: 13px; color: var(--slate-mid); margin: 0; }
.catalog-quality__actions { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
.catalog-quality__stats { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }
.catalog-quality__stats span,
.catalog-quality__groups span { display: inline-flex; gap: 4px; align-items: baseline; border: 1px solid #D6E0E3; border-radius: 8px; padding: 5px 8px; font-size: 12px; color: var(--slate-mid); background: #FAFBFC; }
.catalog-quality__stats strong { color: var(--teal-dark); font-size: 14px; }
.catalog-quality__gap-actions { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 10px; }
.catalog-quality__gap { display: inline-flex; align-items: baseline; gap: 4px; border: 1px solid #D6E0E3; border-radius: 8px; padding: 5px 8px; background: #FFFFFF; color: var(--slate-mid); font-size: 12px; cursor: pointer; }
.catalog-quality__gap strong { color: var(--teal-dark); font-size: 14px; }
.catalog-quality__gap.active { border-color: var(--teal-accent); background: rgba(42,122,110,0.10); color: var(--teal-dark); }
.catalog-quality__gap--empty { opacity: 0.62; }
.catalog-quality__danger strong { color: var(--red-reference); }
.catalog-quality__groups { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 10px; }
.catalog-quality__link { color: var(--teal-accent); font-size: 13px; font-weight: 600; text-decoration: none; }
.catalog-quality__link:hover { text-decoration: underline; }
.catalog-quality__empty { color: var(--slate-mid); font-size: 13px; padding: 8px 0; }
.catalog-import { margin-top: 14px; padding-top: 14px; border-top: 1px solid #E2E8EA; }
.catalog-import__header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 10px; }
.catalog-import__header h4 { font-size: 14px; font-weight: 700; color: var(--teal-dark); margin: 0 0 4px; }
.catalog-import__header p { font-size: 12px; color: var(--slate-mid); margin: 0; }
.catalog-import__preview { display: grid; gap: 10px; }
.catalog-import__stats { display: flex; gap: 8px; flex-wrap: wrap; }
.catalog-import__stats span { display: inline-flex; gap: 4px; align-items: baseline; border: 1px solid #D6E0E3; border-radius: 8px; padding: 5px 8px; font-size: 12px; color: var(--slate-mid); background: #FAFBFC; }
.catalog-import__stats strong { color: var(--teal-dark); font-size: 14px; }
.catalog-import__apply { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.catalog-import__apply span { font-size: 12px; color: var(--slate-mid); }
.catalog-import__history { margin-top: 14px; padding-top: 14px; border-top: 1px solid #E2E8EA; }
.catalog-import__history-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 10px; }
.catalog-import__history-header h4 { font-size: 14px; font-weight: 700; color: var(--teal-dark); margin: 0; }
.catalog-import__history-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
.catalog-import__pagination { display: flex; justify-content: flex-end; margin-top: 10px; }
.catalog-import__details { margin-top: 10px; }
.catalog-import__details-title { font-size: 13px; font-weight: 700; color: var(--teal-dark); margin-bottom: 8px; }
.admin-species-filters { display: grid; grid-template-columns: minmax(220px, 1.4fr) minmax(140px, 1fr) minmax(150px, 1fr) minmax(150px, 1fr) auto auto auto; gap: 8px; align-items: center; margin: 14px 0; padding: 10px; border: 1px solid #D6E0E3; border-radius: 8px; background: #FAFBFC; }
.admin-species-filters__checkbox { min-height: 28px; display: inline-flex; align-items: center; }
.admin-species-filters__meta { font-size: 12px; color: var(--slate-mid); white-space: nowrap; }
.admin-species-quality { display: flex; flex-wrap: wrap; gap: 4px; align-items: center; }
.admin-species-quality__ok { color: var(--slate-mid); font-size: 12px; }
.species-edit-form { max-height: 68vh; overflow-y: auto; padding-right: 4px; }
.species-edit-form__grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 14px; }
.species-form-preview { display: grid; grid-template-columns: 150px 1fr; gap: 14px; margin-top: 14px; padding: 12px; border: 1px solid #D6E0E3; border-radius: 8px; background: #FAFBFC; }
.species-form-preview__image { min-height: 128px; border-radius: 8px; background: #E8EEF0; background-size: cover; background-position: center; display: flex; align-items: center; justify-content: center; color: var(--slate-mid); font-size: 36px; }
.species-form-preview__body { min-width: 0; }
.species-form-preview__eyebrow { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: var(--teal-accent); margin-bottom: 5px; }
.species-form-preview h3 { margin: 0; font-family: var(--font-display); font-size: 22px; line-height: 1.2; color: var(--teal-dark); overflow-wrap: anywhere; }
.species-form-preview__latin { margin-top: 3px; font-style: italic; color: var(--slate-mid); overflow-wrap: anywhere; }
.species-form-preview__tags,
.species-form-preview__facts { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.species-form-preview__tags span { padding: 4px 8px; border-radius: 8px; background: rgba(42,122,110,0.10); color: var(--teal-dark); font-size: 12px; font-weight: 600; }
.species-form-preview p { margin: 9px 0 0; color: var(--slate-mid); font-size: 13px; line-height: 1.5; overflow-wrap: anywhere; }
.species-form-preview__facts span { padding: 5px 8px; border: 1px solid #D6E0E3; border-radius: 8px; color: var(--slate-mid); background: var(--white); font-size: 12px; line-height: 1.35; overflow-wrap: anywhere; }
.upload-area { margin-bottom: 16px; }
.upload-content { padding: 40px; text-align: center; color: var(--slate-mid); }
.upload-content p { margin-top: 8px; font-size: 14px; }
.upload-hint { font-size: 12px; color: var(--slate-light); }
.zone-message { padding: 12px 16px; border-radius: 8px; font-size: 14px; margin-top: 12px; background: rgba(229,57,53,0.1); color: var(--red-reference); }
.zone-message.success { background: rgba(76,175,80,0.1); color: #2E7D32; }
.role-info { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.role-card { background: var(--slate-bg); padding: 20px; border-radius: 12px; }
.role-card h4 { font-size: 16px; font-weight: 700; color: var(--teal-dark); margin-bottom: 8px; }
.role-card p { font-size: 13px; color: var(--slate-mid); }
.ops-summary { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 8px; margin-bottom: 12px; }
.ops-card { border: 1px solid #D6E0E3; border-radius: 8px; padding: 10px 12px; background: #FAFBFC; }
.ops-card--warning { border-color: #E0B15A; background: #FFF9EA; }
.ops-card__title { font-size: 12px; color: var(--slate-mid); margin-bottom: 4px; }
.ops-card__value { font-size: 18px; font-weight: 700; color: var(--teal-dark); line-height: 1.1; }
.ops-card__hint { font-size: 11px; color: var(--slate-mid); margin-top: 2px; }
.ops-alerts { border: 1px solid #D6E0E3; border-radius: 8px; background: #FBFCFD; padding: 10px 12px; margin-bottom: 12px; }
.ops-alerts__header { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 8px; }
.ops-alerts__title { font-size: 13px; font-weight: 600; color: var(--teal-dark); }
.ops-alerts__empty { font-size: 13px; color: var(--slate-mid); }
.ops-alerts__list { display: grid; gap: 8px; }
.ops-alert-item { border: 1px solid #E2E8EA; border-radius: 8px; background: var(--white); padding: 8px 10px; }
.ops-alert-item__message { font-size: 13px; color: var(--teal-dark); line-height: 1.3; }
.ops-alert-item__meta { margin-top: 4px; display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.ops-alert-item__code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 11px; color: var(--teal-dark); }
.ops-alert-item__values { font-size: 11px; color: var(--slate-mid); }
.audit-filters { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px; margin-bottom: 10px; }
.audit-actions { display: flex; justify-content: flex-end; gap: 8px; margin-bottom: 12px; }
.audit-maintenance { display: flex; align-items: center; gap: 8px; margin-right: auto; }
.audit-maintenance__label { font-size: 12px; color: var(--slate-mid); }
.audit-details { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; color: var(--slate-mid); }
.audit-request-id { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; color: var(--slate-mid); }
.audit-pagination { display: flex; justify-content: flex-end; margin-top: 12px; }
@media (max-width: 1080px) {
  .ops-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .audit-filters { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .admin-species-filters { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 920px) {
  .audit-actions {
    flex-wrap: wrap;
    justify-content: flex-start;
  }
  .audit-maintenance {
    width: 100%;
    flex-wrap: wrap;
  }
}
@media (max-width: 768px) { .role-info { grid-template-columns: 1fr; } }
@media (max-width: 768px) { .admin-species-filters { grid-template-columns: 1fr; } }
@media (max-width: 768px) { .species-edit-form__grid { grid-template-columns: 1fr; } }
@media (max-width: 768px) { .species-form-preview { grid-template-columns: 1fr; } }
</style>
