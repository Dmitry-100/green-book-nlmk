<template>
  <div class="quiz-page">
    <h1>Угадай вид</h1>
    <p class="subtitle">Проверьте свои знания о растительном и животном мире площадки</p>

    <div class="quiz-stats">
      <span class="quiz-stat">Правильно: <strong>{{ score }}</strong></span>
      <span class="quiz-stat">Вопрос: <strong>{{ questionNum }}</strong></span>
      <span class="quiz-stat" v-if="streak > 1">Серия: <strong>{{ streak }}</strong></span>
    </div>

    <div v-if="question" class="quiz-card">
      <div class="quiz-photo" :style="{ backgroundImage: `url(${question.photo_url})` }">
        <div class="quiz-photo__badge">{{ groupLabels[question.group] || question.group }}</div>
      </div>
      <div class="quiz-question">Что изображено на фото?</div>
      <div class="quiz-options">
        <button v-for="opt in question.options" :key="opt.id"
                class="quiz-option"
                :class="{
                  correct: answered && opt.id === question.correct_id,
                  wrong: answered && selected === opt.id && opt.id !== question.correct_id,
                  disabled: answered && opt.id !== question.correct_id && selected !== opt.id,
                }"
                :disabled="answered"
                @click="answer(opt.id)">
          <span class="quiz-option__name">{{ opt.name_ru }}</span>
          <span class="quiz-option__latin">{{ opt.name_latin }}</span>
        </button>
      </div>
      <div v-if="answered" class="quiz-feedback" :class="{ 'quiz-feedback--correct': isCorrect, 'quiz-feedback--wrong': !isCorrect }">
        <span v-if="isCorrect">Правильно!</span>
        <span v-else>Неверно. Правильный ответ выделен зелёным.</span>
      </div>
      <button v-if="answered" class="quiz-next" @click="nextQuestion">Следующий вопрос &rarr;</button>
    </div>

    <div v-else class="quiz-loading">Загрузка вопроса...</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api/client'

const question = ref<any>(null)
const selected = ref<number | null>(null)
const answered = ref(false)
const isCorrect = ref(false)
const score = ref(0)
const questionNum = ref(0)
const streak = ref(0)

const groupLabels: Record<string, string> = {
  plants: 'Растения', fungi: 'Грибы', insects: 'Насекомые',
  herpetofauna: 'Герпетофауна', birds: 'Птицы', mammals: 'Млекопитающие',
}

async function loadQuestion() {
  answered.value = false
  selected.value = null
  isCorrect.value = false
  try {
    const { data } = await api.get('/gamification/quiz')
    question.value = data.question !== null ? data : null
    questionNum.value++
  } catch {
    question.value = null
  }
}

function answer(optionId: number) {
  if (answered.value) return
  selected.value = optionId
  answered.value = true
  isCorrect.value = optionId === question.value.correct_id
  if (isCorrect.value) {
    score.value++
    streak.value++
  } else {
    streak.value = 0
  }
}

function nextQuestion() {
  loadQuestion()
}

onMounted(() => loadQuestion())
</script>

<style scoped>
.quiz-page { max-width: 600px; margin: 0 auto; padding: 32px; }
.quiz-page h1 { font-family: 'Cormorant Garamond', serif; font-size: 30px; font-weight: 600; color: #1B4D4F; }
.subtitle { font-size: 14px; color: #8FA5AB; margin-bottom: 20px; }

.quiz-stats { display: flex; gap: 20px; margin-bottom: 20px; }
.quiz-stat { font-size: 14px; color: #4A6572; }
.quiz-stat strong { color: #2A7A6E; font-size: 18px; }

.quiz-card { background: #FAFBFC; border-radius: 20px; overflow: hidden; box-shadow: 0 4px 24px rgba(44,62,74,0.1); }
.quiz-photo {
  width: 100%; height: 300px; background-size: cover; background-position: center;
  position: relative; background-color: #D6E0E3;
}
.quiz-photo__badge {
  position: absolute; top: 12px; left: 12px;
  padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700;
  background: rgba(42,122,110,0.85); color: white; text-transform: uppercase; letter-spacing: 0.5px;
}
.quiz-question { padding: 20px 24px 12px; font-size: 16px; font-weight: 600; color: #2C3E4A; }
.quiz-options { padding: 0 24px 24px; display: flex; flex-direction: column; gap: 8px; }
.quiz-option {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 18px; border: 2px solid #E8EEF0; border-radius: 12px;
  background: white; cursor: pointer; transition: all 0.2s;
}
.quiz-option:hover:not(:disabled) { border-color: #2A7A6E; background: rgba(42,122,110,0.03); }
.quiz-option__name { font-weight: 600; font-size: 14px; color: #2C3E4A; }
.quiz-option__latin { font-style: italic; font-size: 12px; color: #8FA5AB; }
.quiz-option.correct { border-color: #4CAF50; background: rgba(76,175,80,0.08); }
.quiz-option.correct .quiz-option__name { color: #2E7D32; }
.quiz-option.wrong { border-color: #EF5350; background: rgba(239,83,80,0.08); }
.quiz-option.wrong .quiz-option__name { color: #C62828; }
.quiz-option.disabled { opacity: 0.5; cursor: default; }

.quiz-feedback { padding: 12px 24px; font-size: 14px; font-weight: 600; }
.quiz-feedback--correct { color: #2E7D32; }
.quiz-feedback--wrong { color: #C62828; }

.quiz-next {
  display: block; width: calc(100% - 48px); margin: 0 24px 24px;
  padding: 12px; border: none; border-radius: 10px;
  background: #2A7A6E; color: white; font-size: 14px; font-weight: 600;
  cursor: pointer; transition: background 0.2s;
}
.quiz-next:hover { background: #1B4D4F; }

.quiz-loading { text-align: center; padding: 60px; color: #8FA5AB; }
</style>
