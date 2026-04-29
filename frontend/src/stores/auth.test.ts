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

  it('clears only the active auth session when changing tester role', () => {
    localStorage.setItem('auth_token', 'token')
    localStorage.setItem('auth_user', JSON.stringify({
      id: 1,
      displayName: 'Тестовый Пользователь',
      email: 'tester@nlmk.dev',
      role: 'employee',
    }))
    localStorage.setItem('green-book-dev-auth-display-name', 'Тестовый Пользователь')
    localStorage.setItem('green-book-dev-auth-email', 'tester@nlmk.dev')

    const auth = useAuthStore()
    expect(auth.token).toBe('token')

    auth.clearSession()

    expect(auth.token).toBeNull()
    expect(auth.user).toBeNull()
    expect(localStorage.getItem('auth_token')).toBeNull()
    expect(localStorage.getItem('auth_user')).toBeNull()
    expect(localStorage.getItem('green-book-dev-auth-display-name')).toBe('Тестовый Пользователь')
    expect(localStorage.getItem('green-book-dev-auth-email')).toBe('tester@nlmk.dev')
  })
})
