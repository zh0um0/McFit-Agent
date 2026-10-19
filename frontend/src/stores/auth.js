/** 全局状态：登录态、档案、菜单、当日选择。 */
import { defineStore } from 'pinia'
import { api, setTokens, getAccess, onAuthFailure } from '../api/client'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    profile: null,
    loading: false,
    error: '',
    hydrated: false,
  }),

  getters: {
    isLoggedIn: (s) => !!s.user,
    hasProfile: (s) => !!s.profile,
    metrics: (s) => s.profile?.metrics || null,
  },

  actions: {
    async bootstrap() {
      if (this.hydrated) return
      if (getAccess()) {
        try {
          this.user = await api.get('/api/v1/auth/me')
          await this.loadProfile(true)
        } catch {
          setTokens('', '')
          this.user = null
        }
      }
      this.hydrated = true
    },

    async register(payload) {
      return this._auth(() => api.post('/api/v1/auth/register', payload))
    },

    async login(payload) {
      return this._auth(() => api.post('/api/v1/auth/login', payload))
    },

    async _auth(fn) {
      this.loading = true
      this.error = ''
      try {
        const data = await fn()
        setTokens(data.access_token, data.refresh_token)
        this.user = data.user
        await this.loadProfile(true)
        return data.user
      } catch (e) {
        this.error = e.message
        throw e
      } finally {
        this.loading = false
      }
    },

    async loadProfile(silent = false) {
      if (!getAccess()) return
      try {
        this.profile = await api.get('/api/v1/profile')
      } catch (e) {
        if (!silent && e.message !== '尚未建立身材档案') throw e
        this.profile = null
      }
    },

    async saveProfile(payload) {
      this.profile = await api.put('/api/v1/profile', payload)
      return this.profile
    },

    logout() {
      setTokens('', '')
      this.user = null
      this.profile = null
    },
  },
})

// token 刷新失败时自动登出（由 client.js 回调）
onAuthFailure(() => {
  const store = useAuthStore()
  store.logout()
  if (location.hash !== '#/login') location.hash = '#/login'
})