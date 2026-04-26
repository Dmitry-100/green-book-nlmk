<template>
  <Teleport to="body">
    <div
      v-if="modelValue"
      class="species-dialog-backdrop"
      role="presentation"
      @click.self="closeDialog"
    >
      <section
        class="species-edit-dialog"
        role="dialog"
        aria-modal="true"
        :aria-label="title"
        @keydown.esc="closeDialog"
      >
        <header class="species-edit-dialog__header">
          <h2>{{ title }}</h2>
          <button class="species-dialog-icon-button" type="button" aria-label="Закрыть" @click="closeDialog">
            x
          </button>
        </header>

        <form v-if="form" class="species-edit-form" @submit.prevent="$emit('submit')">
          <div class="species-edit-tabs" role="tablist" aria-label="Разделы формы">
            <button
              v-for="tab in speciesFormTabs"
              :key="tab.name"
              class="species-edit-tab"
              type="button"
              role="tab"
              :aria-selected="activeTab === tab.name"
              :class="{ active: activeTab === tab.name }"
              @click="handleActiveTabUpdate(tab.name)"
            >
              {{ tab.label }}
            </button>
          </div>

          <div v-show="activeTab === speciesFormTabs[0].name" class="species-edit-pane">
            <div class="species-edit-form__grid">
              <label class="species-field">
                <span>Название (RU)</span>
                <input v-model="form.name_ru" class="species-native-input" type="text" />
              </label>
              <label class="species-field">
                <span>Латинское название</span>
                <input v-model="form.name_latin" class="species-native-input" type="text" />
              </label>
              <label class="species-field">
                <span>Группа</span>
                <select v-model="form.group" class="species-native-input">
                  <option v-for="option in groupOptions" :key="option.value" :value="option.value">
                    {{ option.label }}
                  </option>
                </select>
              </label>
              <label class="species-field">
                <span>Категория</span>
                <select v-model="form.category" class="species-native-input">
                  <option v-for="option in categoryOptions" :key="option.value" :value="option.value">
                    {{ option.label }}
                  </option>
                </select>
              </label>
            </div>

            <label class="species-field">
              <span>Охранный статус</span>
              <input v-model="form.conservation_status" class="species-native-input" type="text" />
            </label>
            <label class="species-checkbox">
              <input v-model="form.is_poisonous" type="checkbox" />
              <span>Ядовит</span>
            </label>
          </div>

          <div v-show="activeTab === speciesFormTabs[1].name" class="species-edit-pane">
            <label class="species-field">
              <span>Сезонность</span>
              <input v-model="form.season_info" class="species-native-input" type="text" />
            </label>
            <label class="species-field">
              <span>Местообитания</span>
              <textarea v-model="form.biotopes" class="species-native-input species-native-textarea" rows="2" />
            </label>
            <label class="species-field">
              <span>Описание</span>
              <textarea v-model="form.description" class="species-native-input species-native-textarea" rows="4" />
            </label>
            <label class="species-field">
              <span>Памятка</span>
              <textarea v-model="form.do_dont_rules" class="species-native-input species-native-textarea" rows="3" />
            </label>
          </div>

          <div v-show="activeTab === speciesFormTabs[2].name" class="species-edit-pane">
            <label class="species-field">
              <span>Фото, по одному URL на строку</span>
              <textarea v-model="form.photo_urls_text" class="species-native-input species-native-textarea" rows="3" />
            </label>
            <div class="species-edit-form__grid">
              <label class="species-field">
                <span>Аудио URL</span>
                <input v-model="form.audio_url" class="species-native-input" type="text" />
              </label>
              <label class="species-field">
                <span>Название аудио</span>
                <input v-model="form.audio_title" class="species-native-input" type="text" />
              </label>
              <label class="species-field">
                <span>Источник аудио</span>
                <input v-model="form.audio_source" class="species-native-input" type="text" />
              </label>
              <label class="species-field">
                <span>Лицензия аудио</span>
                <input v-model="form.audio_license" class="species-native-input" type="text" />
              </label>
            </div>
          </div>

          <div class="species-form-preview">
            <div
              class="species-form-preview__image"
              :style="preview.photo_url ? { backgroundImage: `url(${preview.photo_url})` } : {}"
            >
              <span v-if="!preview.photo_url">{{ groupIcon(preview.group) }}</span>
            </div>
            <div class="species-form-preview__body">
              <div class="species-form-preview__eyebrow">Предпросмотр карточки</div>
              <h3>{{ preview.name_ru || 'Название вида' }}</h3>
              <div class="species-form-preview__latin">{{ preview.name_latin || 'Latin name' }}</div>
              <div class="species-form-preview__tags">
                <span>{{ groupLabel(preview.group) }}</span>
                <span>{{ categoryLabel(preview.category) }}</span>
                <span v-if="preview.conservation_status">{{ preview.conservation_status }}</span>
                <span v-if="preview.has_audio">Есть голос</span>
                <span v-if="preview.is_poisonous">Ядовит</span>
              </div>
              <p v-if="preview.description">{{ preview.description }}</p>
              <div class="species-form-preview__facts">
                <span v-if="preview.season_info">Когда: {{ preview.season_info }}</span>
                <span v-if="preview.biotopes">Где: {{ preview.biotopes }}</span>
                <span v-if="preview.do_dont_rules">Памятка: {{ preview.do_dont_rules }}</span>
                <span v-if="preview.audio_title">Аудио: {{ preview.audio_title }}</span>
              </div>
            </div>
          </div>

          <footer class="species-edit-dialog__footer">
            <button class="species-dialog-button" type="button" @click="closeDialog">Отмена</button>
            <button class="species-dialog-button species-dialog-button--primary" type="submit" :disabled="saving">
              {{ saving ? 'Сохраняем...' : submitLabel }}
            </button>
          </footer>
        </form>
      </section>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  SPECIES_ADMIN_FORM_TABS,
  buildEmptySpeciesForm,
  buildSpeciesFormPreview,
  type AdminSpeciesEditForm,
} from '../../utils/speciesAdminForm'

const props = withDefaults(defineProps<{
  modelValue: boolean
  title: string
  submitLabel: string
  saving?: boolean
  activeTab: string
  form: AdminSpeciesEditForm | null
}>(), {
  saving: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'update:activeTab': [value: string]
  submit: []
}>()

const speciesFormTabs = SPECIES_ADMIN_FORM_TABS
const preview = computed(() =>
  buildSpeciesFormPreview(props.form || buildEmptySpeciesForm())
)

const groupOptions = [
  { label: 'Растения', value: 'plants', icon: '🌿' },
  { label: 'Грибы', value: 'fungi', icon: '🍄' },
  { label: 'Насекомые', value: 'insects', icon: '🐛' },
  { label: 'Герпетофауна', value: 'herpetofauna', icon: '🐍' },
  { label: 'Птицы', value: 'birds', icon: '🐦' },
  { label: 'Млекопитающие', value: 'mammals', icon: '🦔' },
]
const categoryOptions = [
  { label: 'Рудеральный', value: 'ruderal' },
  { label: 'Типичный', value: 'typical' },
  { label: 'Редкий', value: 'rare' },
  { label: 'Красная книга', value: 'red_book' },
  { label: 'Синантроп', value: 'synanthropic' },
]
const GROUP_LABELS = Object.fromEntries(groupOptions.map((option) => [option.value, option.label]))
const GROUP_ICONS = Object.fromEntries(groupOptions.map((option) => [option.value, option.icon]))
const CATEGORY_LABELS = Object.fromEntries(categoryOptions.map((option) => [option.value, option.label]))

function handleActiveTabUpdate(value: string | number) {
  emit('update:activeTab', String(value))
}

function closeDialog() {
  emit('update:modelValue', false)
}

function groupLabel(group: string): string {
  return GROUP_LABELS[group] || group
}

function groupIcon(group: string): string {
  return GROUP_ICONS[group] || '🌱'
}

function categoryLabel(category: string): string {
  return CATEGORY_LABELS[category] || category
}
</script>

<style scoped>
.species-dialog-backdrop {
  position: fixed;
  inset: 0;
  z-index: 2500;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  overflow-y: auto;
  background: rgba(15, 23, 42, 0.46);
  padding: 6vh 18px 24px;
}

.species-edit-dialog {
  width: min(760px, 100%);
  max-height: 88vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 8px;
  background: var(--white);
  box-shadow: 0 24px 80px rgba(15, 23, 42, 0.28);
}

.species-edit-dialog__header,
.species-edit-dialog__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 18px;
  border-bottom: 1px solid #D6E0E3;
}

.species-edit-dialog__footer {
  justify-content: flex-end;
  border-top: 1px solid #D6E0E3;
  border-bottom: 0;
}

.species-edit-dialog__header h2 {
  margin: 0;
  font-family: var(--font-display);
  font-size: 22px;
  color: var(--teal-dark);
}

.species-dialog-icon-button,
.species-dialog-button {
  border: 1px solid #C9D7DA;
  border-radius: 8px;
  background: #fff;
  color: var(--slate-deep, #2C3E4A);
  cursor: pointer;
  font-weight: 700;
}

.species-dialog-icon-button {
  width: 32px;
  height: 32px;
  font-size: 16px;
  line-height: 1;
}

.species-dialog-button {
  min-height: 36px;
  padding: 0 14px;
}

.species-dialog-button--primary {
  border-color: var(--teal, #2F7D62);
  background: var(--teal, #2F7D62);
  color: #fff;
}

.species-dialog-button:hover:not(:disabled),
.species-dialog-icon-button:hover:not(:disabled) {
  border-color: var(--teal-accent, #2A7A6E);
  color: var(--teal-dark, #1E5F57);
}

.species-dialog-button--primary:hover:not(:disabled) {
  background: var(--teal-dark, #1E5F57);
  color: #fff;
}

.species-dialog-button:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.species-edit-form {
  min-height: 0;
  overflow-y: auto;
  padding: 14px 18px 0;
}

.species-edit-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 14px;
  border-bottom: 1px solid #D6E0E3;
}

.species-edit-tab {
  border: 0;
  border-radius: 8px 8px 0 0;
  background: transparent;
  color: var(--slate-mid);
  cursor: pointer;
  font-size: 13px;
  font-weight: 800;
  padding: 10px 12px;
}

.species-edit-tab.active {
  background: rgba(42, 122, 110, 0.10);
  color: var(--teal-dark);
}

.species-edit-pane {
  display: grid;
  gap: 12px;
}

.species-edit-form__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 14px;
}

.species-field,
.species-checkbox {
  display: grid;
  gap: 6px;
  color: var(--slate-deep, #2C3E4A);
  font-size: 13px;
  font-weight: 700;
}

.species-checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
}

.species-native-input {
  width: 100%;
  min-width: 0;
  border: 1px solid #D6E0E3;
  border-radius: 8px;
  background: #fff;
  color: var(--slate-deep, #2C3E4A);
  font: inherit;
  font-size: 14px;
  font-weight: 500;
  min-height: 36px;
  padding: 8px 10px;
}

.species-native-textarea {
  resize: vertical;
  line-height: 1.45;
}

.species-native-input:focus,
.species-edit-tab:focus-visible,
.species-dialog-button:focus-visible,
.species-dialog-icon-button:focus-visible {
  outline: 2px solid var(--teal-accent, #2A7A6E);
  outline-offset: 2px;
}

.species-form-preview {
  display: grid;
  grid-template-columns: 150px 1fr;
  gap: 14px;
  margin-top: 14px;
  padding: 12px;
  border: 1px solid #D6E0E3;
  border-radius: 8px;
  background: #FAFBFC;
}

.species-form-preview__image {
  min-height: 128px;
  border-radius: 8px;
  background: #E8EEF0;
  background-size: cover;
  background-position: center;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--slate-mid);
  font-size: 36px;
}

.species-form-preview__body {
  min-width: 0;
}

.species-form-preview__eyebrow {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  color: var(--teal-accent);
  margin-bottom: 5px;
}

.species-form-preview h3 {
  margin: 0;
  font-family: var(--font-display);
  font-size: 22px;
  line-height: 1.2;
  color: var(--teal-dark);
  overflow-wrap: anywhere;
}

.species-form-preview__latin {
  margin-top: 3px;
  font-style: italic;
  color: var(--slate-mid);
  overflow-wrap: anywhere;
}

.species-form-preview__tags,
.species-form-preview__facts {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.species-form-preview__tags span {
  padding: 4px 8px;
  border-radius: 8px;
  background: rgba(42, 122, 110, 0.10);
  color: var(--teal-dark);
  font-size: 12px;
  font-weight: 600;
}

.species-form-preview p {
  margin: 9px 0 0;
  color: var(--slate-mid);
  font-size: 13px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.species-form-preview__facts span {
  padding: 5px 8px;
  border: 1px solid #D6E0E3;
  border-radius: 8px;
  color: var(--slate-mid);
  background: var(--white);
  font-size: 12px;
  line-height: 1.35;
  overflow-wrap: anywhere;
}

@media (max-width: 768px) {
  .species-dialog-backdrop {
    padding: 12px;
  }

  .species-edit-form__grid,
  .species-form-preview {
    grid-template-columns: 1fr;
  }
}
</style>
