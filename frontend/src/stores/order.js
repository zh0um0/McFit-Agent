/** 点餐工作台状态：菜单、勾选、凑单结果。 */
import { defineStore } from 'pinia'
import { api } from '../api/client'

export const useOrderStore = defineStore('order', {
  state: () => ({
    meals: [],
    categories: [],
    source: 'seed',
    disclaimer: '',
    selected: [],
    category: '',
    highProteinOnly: false,
    excludeFried: false,
    keyword: '',
    calc: null,
    coupons: [],
    loading: false,
    error: '',
  }),

  getters: {
    selectedMeals: (s) => s.selected.map((c) => s.meals.find((m) => m.code === c)).filter(Boolean),
    totalKcal: (s) => s.selected.reduce((a, c) => {
      const m = s.meals.find((x) => x.code === c)
      return a + (m?.kcal || 0)
    }, 0),
    totalProtein: (s) => s.selected.reduce((a, c) => {
      const m = s.meals.find((x) => x.code === c)
      return a + (m?.protein_g || 0)
    }, 0),
    totalPrice: (s) => s.selected.reduce((a, c) => {
      const m = s.meals.find((x) => x.code === c)
      return a + (m?.price || 0)
    }, 0),
    filtered: (s) => s.meals.filter((m) => {
      if (s.category && m.category !== s.category) return false
      if (s.highProteinOnly && !m.is_high_protein) return false
      if (s.excludeFried && m.is_fried) return false
      if (s.keyword && !m.name.includes(s.keyword)) return false
      return true
    }),
    byCategory: (s) => {
      const map = {}
      for (const m of s.filtered) (map[m.category] ||= []).push(m)
      return map
    },
  },

  actions: {
    async loadMeals() {
      this.loading = true
      this.error = ''
      try {
        const data = await api.get('/api/v1/meals')
        this.meals = data.items
        this.categories = data.categories
        this.source = data.source
        this.disclaimer = data.disclaimer
      } catch (e) {
        this.error = e.message
      } finally {
        this.loading = false
      }
    },

    async loadCoupons() {
      try {
        this.coupons = (await api.get('/api/v1/coupons')).items || []
      } catch {
        this.coupons = []
      }
    },

    toggle(code) {
      const i = this.selected.indexOf(code)
      if (i >= 0) this.selected.splice(i, 1)
      else this.selected.push(code)
    },

    clear() {
      this.selected = []
      this.calc = null
    },

    applyRecommendation() {
      const next = (this.calc?.meals || []).map((m) => m.code)
      if (next.length) {
        this.selected = next
        this.calculate()
      }
    },

    async calculate() {
      if (!this.selected.length) {
        this.calc = null
        return
      }
      try {
        this.calc = await api.post('/api/v1/meals/calculate', { codes: this.selected })
      } catch (e) {
        this.error = e.message
      }
    },
  },
})