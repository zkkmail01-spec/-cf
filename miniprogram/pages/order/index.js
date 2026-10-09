const api = require('../../utils/api');
const orderState = require('../../utils/order-state');

Page({
  data: { state: null, categories: [], dishes: [], visibleDishes: [], categoryId: '', query: '', loading: true, error: '', pendingDishId: '', selectedCount: 0 },
  onLoad(options) {
    this.setData({ state: orderState.createOrderState({ date: options.date, mealType: options.mealType }) });
    this.loadData();
  },
  async loadData() {
    this.setData({ loading: true, error: '' });
    try {
      const [categories, dishes, day] = await Promise.all([
        api.request({ path: '/categories' }), api.request({ path: '/dishes' }), api.request({ path: `/meals/${this.data.state.date}` }),
      ]);
      const openid = getApp().globalData.session && getApp().globalData.session.identity.openid;
      const selectionsByMeal = {};
      orderState.MEAL_TYPES.forEach((type) => {
        selectionsByMeal[type] = day.meals[type].items.filter((item) => item.selectors.some((person) => person.openid === openid)).map((item) => item.dishId);
      });
      const state = orderState.createOrderState({ ...this.data.state, selectionsByMeal });
      this.setData({ categories, dishes, visibleDishes: orderState.decorateDishes(dishes, state), state, selectedCount: orderState.selectedCount(state), loading: false });
    } catch (error) { this.setData({ loading: false, error: error.message || '加载失败' }); }
  },
  changeMeal(event) { const state = orderState.switchMeal(this.data.state, event.detail.value); this.setData({ state, selectedCount: orderState.selectedCount(state) }); this.applyFilters(); },
  chooseCategory(event) { this.setData({ categoryId: event.currentTarget.dataset.id || '' }); this.applyFilters(); },
  onSearch(event) { this.setData({ query: event.detail.value }); this.applyFilters(); },
  applyFilters() { const filtered = orderState.filterDishes(this.data.dishes, { categoryId: this.data.categoryId, query: this.data.query }); this.setData({ visibleDishes: orderState.decorateDishes(filtered, this.data.state) }); },
  async toggleDish(event) {
    const dishId = event.detail.dish.id;
    const selected = !orderState.selectedIds(this.data.state).includes(dishId);
    const state = orderState.toggleDish(this.data.state, dishId);
    this.setData({ state, selectedCount: orderState.selectedCount(state), pendingDishId: dishId, error: '' }); this.applyFilters();
    try { await orderState.submitDish(state, dishId, selected, api.request); wx.showToast({ title: selected ? '已加入' : '已取消', icon: 'success' }); }
    catch (error) { this.setData({ error: `${error.message || '提交失败'}，选择已保留，可再次点击重试` }); }
    finally { this.setData({ pendingDishId: '' }); }
  },
});
