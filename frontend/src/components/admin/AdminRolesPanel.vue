<template>
  <div>
    <h2>Управление ролями</h2>
    <p class="admin-hint">
      Роли назначаются при первом входе через SSO. Здесь можно повысить сотрудника до эколога или администратора.
    </p>
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
</template>

<style scoped>
.admin-hint {
  font-size: 14px;
  color: var(--slate-mid);
  margin-bottom: 20px;
}

.role-info {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.role-card {
  background: var(--slate-bg);
  padding: 20px;
  border-radius: 8px;
}

.role-card h4 {
  font-size: 16px;
  font-weight: 700;
  color: var(--teal-dark);
  margin-bottom: 8px;
}

.role-card p {
  font-size: 13px;
  color: var(--slate-mid);
}

@media (max-width: 768px) {
  .role-info {
    grid-template-columns: 1fr;
  }
}
</style>
