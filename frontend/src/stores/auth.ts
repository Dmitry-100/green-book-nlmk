import { defineStore } from 'pinia'
import { ref } from 'vue'

interface UserInfo {
  id: number
  displayName: string
  email: string
  role: 'employee' | 'ecologist' | 'admin'
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('auth_token'))
  const user = ref<UserInfo | null>(JSON.parse(localStorage.getItem('auth_user') || 'null'))

  function setToken(t: string) {
    token.value = t
    localStorage.setItem('auth_token', t)
  }

  function setUser(u: UserInfo) {
    user.value = u
    localStorage.setItem('auth_user', JSON.stringify(u))
  }

  function clearSession() {
    token.value = null
    user.value = null
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_user')
  }

  function isEcologist() {
    return user.value?.role === 'ecologist' || user.value?.role === 'admin'
  }

  function isAdmin() {
    return user.value?.role === 'admin'
  }

  return { token, user, setToken, setUser, clearSession, isEcologist, isAdmin }
})
