<template>
  <div class="help-page">
    <h1>Правила и помощь</h1>
    <p class="subtitle">Инструкции для безопасного наблюдения на промплощадке</p>

    <div class="help-grid">
      <div class="help-card">
        <div class="help-card__icon">🦺</div>
        <h3>Техника безопасности</h3>
        <ul>
          <li>Наблюдения проводите только в разрешённых зонах</li>
          <li>Не покидайте безопасные маршруты и дорожки</li>
          <li>Используйте средства индивидуальной защиты</li>
          <li>Не приближайтесь к диким животным</li>
          <li>При обнаружении опасных животных (кабан, гадюка) немедленно сообщите экологу</li>
        </ul>
      </div>

      <div class="help-card">
        <div class="help-card__icon">📸</div>
        <h3>Как сделать наблюдение</h3>
        <ol>
          <li>Выберите группу (растение, гриб, птица и т.д.)</li>
          <li>Укажите дату, время и место на карте</li>
          <li>Сделайте фото (минимум 1)</li>
          <li>Опишите наблюдение: количество, поведение, особенности</li>
          <li>Подтвердите соблюдение ТБ и отправьте</li>
        </ol>
      </div>

      <div class="help-card">
        <div class="help-card__icon">🔍</div>
        <h3>Определение вида</h3>
        <ul>
          <li>Используйте <router-link to="/identify">Определитель</router-link> — пошаговый помощник</li>
          <li>Если не знаете вид — укажите только группу, эколог определит</li>
          <li>Фотографируйте с разных ракурсов для точного определения</li>
          <li>Для растений — снимайте листья, цветы, общий вид</li>
          <li>Для птиц — снимайте издалека с зумом, не спугните</li>
        </ul>
      </div>

      <div class="help-card">
        <div class="help-card__icon">🚨</div>
        <h3>Когда сообщать инцидент</h3>
        <ul>
          <li>Раненое или погибшее животное</li>
          <li>Массовая гибель (птиц, рыб, насекомых)</li>
          <li>Агрессивное поведение животного</li>
          <li>Разрушение гнёзд или нор</li>
          <li>Инцидент = приоритетная обработка экологом</li>
        </ul>
      </div>

      <div class="help-card help-card--wide">
        <div class="help-card__icon">📋</div>
        <h3>Статусы наблюдений</h3>
        <div class="status-grid">
          <div class="status-item">
            <span class="status-dot status-dot--review"></span>
            <div><strong>На проверке</strong><br>Отправлено, ожидает проверки экологом</div>
          </div>
          <div class="status-item">
            <span class="status-dot status-dot--needs-data"></span>
            <div><strong>Нужны данные</strong><br>Эколог запросил уточнения — дополните наблюдение</div>
          </div>
          <div class="status-item">
            <span class="status-dot status-dot--confirmed"></span>
            <div><strong>Подтверждено</strong><br>Вид определён и подтверждён экологом</div>
          </div>
          <div class="status-item">
            <span class="status-dot status-dot--rejected"></span>
            <div><strong>Отклонено</strong><br>Не удалось определить или данные некорректны</div>
          </div>
        </div>
      </div>

      <div class="help-card">
        <div class="help-card__icon">📞</div>
        <h3>Контакты</h3>
        <p>Служба экологии ПАО «НЛМК»</p>
        <p class="contact">Управление технической защиты</p>
        <p class="contact-note">По вопросам работы портала обращайтесь к администратору раздела.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.help-page { max-width: 1000px; margin: 0 auto; padding: 32px; }
.help-page h1 { font-family: var(--font-display); font-size: 30px; font-weight: 600; color: var(--teal-dark); }
.subtitle { font-size: 14px; color: var(--slate-mid); margin-bottom: 28px; }
.help-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.help-card {
  background: var(--white); border-radius: var(--radius-lg); padding: 28px;
  box-shadow: var(--shadow-card);
}
.help-card--wide { grid-column: 1 / -1; }
.help-card__icon { font-size: 36px; margin-bottom: 12px; }
.help-card h3 { font-family: var(--font-display); font-size: 20px; font-weight: 600; color: var(--teal-dark); margin-bottom: 14px; }
.help-card ul, .help-card ol { padding-left: 20px; color: var(--slate-mid); font-size: 14px; line-height: 2; }
.help-card li { margin-bottom: 2px; }
.help-card p { font-size: 14px; color: var(--slate-mid); line-height: 1.7; }
.help-card a { color: var(--teal); font-weight: 600; }
.contact { font-weight: 600; color: var(--slate-deep); margin-top: 8px; }
.contact-note { font-size: 12px; color: var(--slate-light); margin-top: 8px; }
.status-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.status-item { display: flex; align-items: flex-start; gap: 12px; font-size: 13px; color: var(--slate-mid); }
.status-dot { width: 14px; height: 14px; border-radius: 50%; flex-shrink: 0; margin-top: 4px; }
.status-dot--review { background: var(--yellow-potential); }
.status-dot--needs-data { background: #2196F3; }
.status-dot--confirmed { background: var(--green-confirm); }
.status-dot--rejected { background: var(--red-reference); }
@media (max-width: 768px) { .help-grid { grid-template-columns: 1fr; } .status-grid { grid-template-columns: 1fr; } }
</style>
