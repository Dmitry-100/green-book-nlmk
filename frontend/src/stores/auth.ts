import { defineStore } from 'pinia'
import { ref } from 'vue'

interface UserInfo {
  id: number
  displayName: string
  publicName: string
  email: string | null
  role: 'employee' | 'ecologist' | 'admin'
  approvalStatus: 'pending' | 'approved' | 'rejected'
  isActive: boolean
  mustChangePassword: boolean
}

export const useAuthStore = defineStore('auth', () => {
  localStorage.removeItem('auth_token')
  const token = ref<string | null>(null)
  const user = ref<UserInfo | null>(JSON.parse(localStorage.getItem('auth_user') || 'null'))

  function setToken(t: string) {
    token.value = t
  }

  function setUser(u: UserInfo) {
    user.value = u
    localStorage.setItem('auth_user', JSON.stringify(u))
  }

  function setSession(t: string, u: UserInfo) {
    setToken(t)
    setUser(u)
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

  function isAuthenticated() {
    return Boolean(token.value || user.value)
  }

  return {
    token,
    user,
    setToken,
    setUser,
    setSession,
    clearSession,
    isAuthenticated,
    isEcologist,
    isAdmin,
  }
})
