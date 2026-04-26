<template>
  <Teleport to="body">
    <div v-if="confirmOpen" class="expert-dialog-backdrop" @click.self="closeConfirm">
      <section class="expert-dialog" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
        <header class="expert-dialog__header">
          <h2 id="confirm-title">Подтвердить наблюдение</h2>
          <button class="expert-dialog__close" type="button" aria-label="Закрыть" @click="closeConfirm">
            x
          </button>
        </header>

        <div class="expert-dialog__body expert-confirm-form">
          <label class="expert-field">
            <span>Определённый вид</span>
            <input
              v-model="speciesSearch"
              class="expert-input"
              placeholder="Найти вид по названию или латыни"
              :disabled="speciesLoading"
            />
          </label>

          <label class="expert-field">
            <span>Выбор вида</span>
            <select
              class="expert-select"
              :value="confirmForm.species_id ?? ''"
              :disabled="speciesLoading"
              @change="onSpeciesChange"
            >
              <option value="">{{ speciesLoading ? 'Загружаем виды...' : 'Не менять вид' }}</option>
              <option
                v-for="species in filteredSpeciesOptions"
                :key="species.id"
                :value="species.id"
              >
                {{ species.name_ru }} ({{ species.name_latin }})
              </option>
            </select>
          </label>

          <label class="expert-field">
            <span>Чувствительность координат</span>
            <select v-model="confirmForm.sensitive_level" class="expert-select">
              <option value="open">Открытые координаты</option>
              <option value="blurred">Размытые координаты</option>
              <option value="hidden">Скрытые координаты</option>
            </select>
          </label>

          <label class="expert-field">
            <span>Комментарий</span>
            <textarea
              v-model="confirmForm.comment"
              class="expert-textarea"
              rows="3"
              placeholder="Комментарий к решению"
            />
          </label>
          <p v-if="confirmError" class="dialog-error">{{ confirmError }}</p>
        </div>

        <footer class="expert-dialog__footer">
          <button class="expert-button" type="button" @click="closeConfirm">Отмена</button>
          <button
            class="expert-button expert-button--success"
            type="button"
            :disabled="confirmLoading"
            @click="$emit('confirm')"
          >
            {{ confirmLoading ? 'Подтверждаем...' : 'Подтвердить' }}
          </button>
        </footer>
      </section>
    </div>

    <div v-if="requestOpen" class="expert-dialog-backdrop" @click.self="closeRequest">
      <section class="expert-dialog expert-dialog--small" role="dialog" aria-modal="true" aria-labelledby="request-title">
        <header class="expert-dialog__header">
          <h2 id="request-title">Запросить уточнения</h2>
          <button class="expert-dialog__close" type="button" aria-label="Закрыть" @click="closeRequest">
            x
          </button>
        </header>

        <div class="expert-dialog__body">
          <label class="expert-field">
            <span>Что нужно уточнить?</span>
            <textarea
              class="expert-textarea"
              rows="3"
              :value="actionComment"
              placeholder="Что нужно уточнить?"
              @input="updateActionComment"
            />
          </label>
        </div>

        <footer class="expert-dialog__footer">
          <button class="expert-button" type="button" @click="closeRequest">Отмена</button>
          <button class="expert-button expert-button--primary" type="button" @click="$emit('request')">
            Отправить
          </button>
        </footer>
      </section>
    </div>

    <div v-if="rejectOpen" class="expert-dialog-backdrop" @click.self="closeReject">
      <section class="expert-dialog expert-dialog--small" role="dialog" aria-modal="true" aria-labelledby="reject-title">
        <header class="expert-dialog__header">
          <h2 id="reject-title">Отклонить наблюдение</h2>
          <button class="expert-dialog__close" type="button" aria-label="Закрыть" @click="closeReject">
            x
          </button>
        </header>

        <div class="expert-dialog__body">
          <label class="expert-field">
            <span>Причина отклонения</span>
            <textarea
              class="expert-textarea"
              rows="3"
              :value="actionComment"
              placeholder="Причина отклонения"
              @input="updateActionComment"
            />
          </label>
        </div>

        <footer class="expert-dialog__footer">
          <button class="expert-button" type="button" @click="closeReject">Отмена</button>
          <button class="expert-button expert-button--danger" type="button" @click="$emit('reject')">
            Отклонить
          </button>
        </footer>
      </section>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

type SpeciesOption = {
  id: number
  name_ru: string
  name_latin: string
}

type ConfirmForm = {
  species_id: number | null
  sensitive_level: string
  comment: string
}

const props = defineProps<{
  confirmOpen: boolean
  requestOpen: boolean
  rejectOpen: boolean
  actionComment: string
  confirmForm: ConfirmForm
  speciesOptions: SpeciesOption[]
  speciesLoading: boolean
  confirmLoading: boolean
  confirmError: string
}>()

const emit = defineEmits<{
  'update:confirmOpen': [value: boolean]
  'update:requestOpen': [value: boolean]
  'update:rejectOpen': [value: boolean]
  'update:actionComment': [value: string]
  confirm: []
  request: []
  reject: []
}>()

const speciesSearch = ref('')

const filteredSpeciesOptions = computed(() => {
  const query = speciesSearch.value.trim().toLowerCase()
  if (!query) {
    return props.speciesOptions
  }
  return props.speciesOptions.filter((species) => (
    species.name_ru.toLowerCase().includes(query)
    || species.name_latin.toLowerCase().includes(query)
  ))
})

watch(
  () => props.confirmOpen,
  (isOpen) => {
    if (!isOpen) {
      speciesSearch.value = ''
    }
  }
)

function onSpeciesChange(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  props.confirmForm.species_id = value ? Number(value) : null
}

function updateActionComment(event: Event) {
  emit('update:actionComment', (event.target as HTMLTextAreaElement).value)
}

function closeConfirm() {
  emit('update:confirmOpen', false)
}

function closeRequest() {
  emit('update:requestOpen', false)
}

function closeReject() {
  emit('update:rejectOpen', false)
}
</script>

<style scoped>
.expert-dialog-backdrop {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 18px;
  background: rgba(18, 34, 39, 0.42);
}

.expert-dialog {
  width: min(100%, 460px);
  max-height: min(720px, calc(100vh - 36px));
  overflow: auto;
  border: 1px solid rgba(214, 224, 227, 0.9);
  border-radius: 8px;
  background: #FFFFFF;
  box-shadow: 0 18px 54px rgba(18, 34, 39, 0.22);
}

.expert-dialog--small {
  width: min(100%, 400px);
}

.expert-dialog__header,
.expert-dialog__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
}

.expert-dialog__header {
  border-bottom: 1px solid #E6ECEE;
}

.expert-dialog__header h2 {
  margin: 0;
  color: #1B4D4F;
  font-size: 18px;
  font-weight: 800;
}

.expert-dialog__close {
  width: 30px;
  height: 30px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  color: #6B7C86;
  cursor: pointer;
  font-size: 16px;
}

.expert-dialog__close:hover {
  border-color: #C9D7DA;
  background: #F4F8F9;
  color: #1E5F57;
}

.expert-dialog__body {
  padding: 16px;
}

.expert-dialog__footer {
  justify-content: flex-end;
  border-top: 1px solid #E6ECEE;
}

.expert-confirm-form,
.expert-field {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.expert-field span {
  font-size: 13px;
  font-weight: 700;
  color: #2C3E4A;
}

.expert-input,
.expert-select,
.expert-textarea {
  width: 100%;
  min-width: 0;
  border: 1px solid #D6E0E3;
  border-radius: 8px;
  background: #fff;
  color: #2C3E4A;
  font: inherit;
  font-size: 13px;
}

.expert-input,
.expert-select {
  height: 34px;
  padding: 0 10px;
}

.expert-select {
  padding-right: 28px;
}

.expert-textarea {
  min-height: 82px;
  padding: 9px 10px;
  resize: vertical;
}

.expert-input:focus,
.expert-select:focus,
.expert-textarea:focus {
  outline: none;
  border-color: #2A7A6E;
  box-shadow: 0 0 0 2px rgba(42, 122, 110, 0.12);
}

.expert-input:disabled,
.expert-select:disabled {
  cursor: wait;
  opacity: 0.68;
}

.expert-button {
  min-height: 32px;
  border: 1px solid #C9D7DA;
  border-radius: 8px;
  padding: 0 12px;
  background: #FFFFFF;
  color: #2C3E4A;
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  font-weight: 800;
}

.expert-button:hover:not(:disabled) {
  border-color: #2A7A6E;
  color: #1E5F57;
}

.expert-button:focus-visible,
.expert-dialog__close:focus-visible {
  outline: 2px solid #2A7A6E;
  outline-offset: 2px;
}

.expert-button:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.expert-button--primary {
  border-color: #2A7A6E;
  background: #2A7A6E;
  color: #FFFFFF;
}

.expert-button--success {
  border-color: #2E7D32;
  background: #2E7D32;
  color: #FFFFFF;
}

.expert-button--danger {
  border-color: #C62828;
  background: #C62828;
  color: #FFFFFF;
}

.expert-button--primary:hover:not(:disabled),
.expert-button--success:hover:not(:disabled),
.expert-button--danger:hover:not(:disabled) {
  filter: brightness(0.94);
  color: #FFFFFF;
}

.dialog-error {
  margin: 2px 0 0;
  color: #E53935;
  font-size: 12px;
  font-weight: 700;
}

@media (max-width: 560px) {
  .expert-dialog-backdrop {
    align-items: flex-end;
    padding: 10px;
  }

  .expert-dialog,
  .expert-dialog--small {
    width: 100%;
  }
}
</style>
