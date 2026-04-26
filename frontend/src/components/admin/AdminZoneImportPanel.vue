<template>
  <div>
    <h2>Импорт зон площадки</h2>
    <p class="admin-hint">Загрузите GeoJSON-файл с полигонами зон промплощадки.</p>
    <label
      class="upload-area"
      :class="{ dragging: dragActive, disabled: uploading }"
      @dragenter.prevent="dragActive = true"
      @dragover.prevent="dragActive = true"
      @dragleave.prevent="dragActive = false"
      @drop.prevent="handleDrop"
    >
      <input
        type="file"
        accept=".geojson,.json,application/json,geo+json"
        :disabled="uploading"
        @change="handleFileChange"
      />
      <div class="upload-content">
        <span class="upload-content__icon">📁</span>
        <p>{{ uploading ? 'Загружаем GeoJSON...' : 'Перетащите GeoJSON-файл или нажмите для выбора' }}</p>
        <p class="upload-hint">Поддерживаемые форматы: .geojson, .json</p>
      </div>
    </label>
    <div v-if="message" class="zone-message" :class="{ success }">{{ message }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  headers: Record<string, string>
  message: string
  success: boolean
}>()

const emit = defineEmits<{
  success: [response: unknown]
  error: []
}>()

const uploading = ref(false)
const dragActive = ref(false)

async function uploadZoneFile(file: File) {
  uploading.value = true
  const formData = new FormData()
  formData.append('file', file)
  try {
    const response = await fetch('/api/admin/zones/import', {
      method: 'POST',
      headers: props.headers,
      body: formData,
    })
    if (!response.ok) {
      throw new Error(`Zone import failed with status ${response.status}`)
    }
    emit('success', await response.json())
  } catch {
    emit('error')
  } finally {
    uploading.value = false
  }
}

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) {
    void uploadZoneFile(file)
  }
  input.value = ''
}

function handleDrop(event: DragEvent) {
  dragActive.value = false
  const file = event.dataTransfer?.files?.[0]
  if (file && !uploading.value) {
    void uploadZoneFile(file)
  }
}
</script>

<style scoped>
.admin-hint {
  font-size: 14px;
  color: var(--slate-mid);
  margin-bottom: 20px;
}

.upload-area {
  display: block;
  margin-bottom: 16px;
  border: 1px dashed #B8C9CE;
  border-radius: 8px;
  background: #FAFBFC;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease;
}

.upload-area:hover,
.upload-area.dragging {
  border-color: var(--teal-accent);
  background: #F0F7F6;
}

.upload-area.disabled {
  cursor: wait;
  opacity: 0.72;
}

.upload-area input {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.upload-area:focus-within {
  outline: 2px solid var(--teal-accent);
  outline-offset: 2px;
}

.upload-content {
  padding: 40px;
  text-align: center;
  color: var(--slate-mid);
}

.upload-content__icon {
  font-size: 36px;
}

.upload-content p {
  margin-top: 8px;
  font-size: 14px;
}

.upload-hint {
  font-size: 12px;
  color: var(--slate-light);
}

.zone-message {
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 14px;
  margin-top: 12px;
  background: rgba(229, 57, 53, 0.1);
  color: var(--red-reference);
}

.zone-message.success {
  background: rgba(76, 175, 80, 0.1);
  color: #2E7D32;
}
</style>
