const api = require('../../utils/api');
const { filterDishes } = require('../../utils/order-state');

Page({
  data: { dishes: [], visibleDishes: [], categories: [], categoryId: '', query: '', isChef: false, loading: true, error: '', newCategory: '' },
  onShow() { this.loadDishes(); },
  async loadDishes() {
    this.setData({ loading: true, error: '' });
    try {
      const [session, categories, dishes] = await Promise.all([api.request({ path: '/session' }), api.request({ path: '/categories' }), api.request({ path: '/dishes' })]);
      this.setData({ categories, dishes, visibleDishes: dishes, isChef: session.member.role === 'chef', loading: false });
    } catch (error) { this.setData({ loading: false, error: error.message || '加载失败' }); }
  },
  onSearch(event) { this.setData({ query: event.detail.value }); this.applyFilters(); },
  chooseCategory(event) { this.setData({ categoryId: event.currentTarget.dataset.id || '' }); this.applyFilters(); },
  applyFilters() { this.setData({ visibleDishes: filterDishes(this.data.dishes, { categoryId: this.data.categoryId, query: this.data.query }) }); },
  addDish() { wx.navigateTo({ url: '/pages/dish-edit/index' }); },
  editDish(event) { wx.navigateTo({ url: `/pages/dish-edit/index?id=${event.detail.dish.id}` }); },
  onNewCategory(event) { this.setData({ newCategory: event.detail.value }); },
  async addCategory() {
    const name = this.data.newCategory.trim(); if (!name) return;
    try { await api.request({ path: '/categories', method: 'POST', data: { name }, idempotent: true }); this.setData({ newCategory: '' }); await this.loadDishes(); }
    catch (error) { this.setData({ error: error.message || '新增分类失败' }); }
  },
});
