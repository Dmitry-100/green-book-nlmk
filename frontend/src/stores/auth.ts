import { defineStore } from 'pinia'
import { ref } from 'vue'

interface UserInfo {
  id: number
  displayName: string
  email: string
  role: 'employee' | 'ecologist' | 'admin'
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(null)
  const user = ref<UserInfo | null>(null)

  function setToken(t: string) {
    token.value = t
  }

  function setUser(u: UserInfo) {
    user.value = u
  }

  function isEcologist() {
    return user.value?.role === 'ecologist' || user.value?.role === 'admin'
  }

  function isAdmin() {
    return user.value?.role === 'admin'
  }

  return { token, user, setToken, setUser, isEcologist, isAdmin }
})
