import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from './auth'

function createMemoryStorage(): Storage {
  const data = new Map<string, string>()

  return {
    get length() {
      return data.size
    },
    clear() {
      data.clear()
    },
    getItem(key: string) {
      return data.get(key) ?? null
    },
    key(index: number) {
      return Array.from(data.keys())[index] ?? null
    },
    removeItem(key: string) {
      data.delete(key)
    },
    setItem(key: string, value: string) {
      data.set(key, value)
    },
  }
}

describe('auth store', () => {
  beforeEach(() => {
    Object.defineProperty(globalThis, 'localStorage', {
      value: createMemoryStorage(),
      configurable: true,
    })
    setActivePinia(createPinia())
  })

  it('keeps auth token out of localStorage and clears user state', () => {
    localStorage.setItem('auth_user', JSON.stringify({
      id: 1,
      displayName: 'Тестовый Пользователь',
      publicName: 'ТП',
      email: null,
      role: 'employee',
      approvalStatus: 'approved',
      isActive: true,
      mustChangePassword: false,
    }))

    const auth = useAuthStore()
    auth.setSession('token', {
      id: 2,
      displayName: 'Наблюдатель',
      publicName: 'Н',
      email: null,
      role: 'employee',
      approvalStatus: 'approved',
      isActive: true,
      mustChangePassword: false,
    })

    expect(auth.token).toBe('token')
    expect(localStorage.getItem('auth_token')).toBeNull()
    expect(localStorage.getItem('auth_user')).toContain('Наблюдатель')

    auth.clearSession()

    expect(auth.token).toBeNull()
    expect(auth.user).toBeNull()
    expect(localStorage.getItem('auth_token')).toBeNull()
    expect(localStorage.getItem('auth_user')).toBeNull()
  })
})
