const api = require('../../utils/api');
const orderState = require('../../utils/order-state');
const drafts = require('../../utils/meal-draft');
const dates = require('../../utils/date');

Page({
  data: { state: null, minDate: '', maxDate: '', serverSelectionsByMeal: {}, pendingOperations: [], categories: [], dishes: [], visibleDishes: [], categoryId: '', query: '', loading: true, error: '', pendingDishId: '', selectedCount: 0 },
  onLoad(options) {
    const today = dates.formatLocalDate();
    this.setData({ minDate: today, maxDate: dates.shiftDate(today, 3), state: orderState.createOrderState({ date: options.date || today, mealType: options.mealType }) });
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
      let state = orderState.createOrderState({ ...this.data.state, selectionsByMeal });
      let pendingOperations = [];
      if (drafts.hasDraft(state.date, state.mealType)) {
        const draftIds = drafts.loadDraft(state.date, state.mealType);
        pendingOperations = orderState.pendingOperations(selectionsByMeal[state.mealType], draftIds);
        state = { ...state, selectionsByMeal: { ...state.selectionsByMeal, [state.mealType]: draftIds } };
      }
      this.setData({ categories, dishes, serverSelectionsByMeal: selectionsByMeal, pendingOperations, visibleDishes: orderState.decorateDishes(dishes, state), state, selectedCount: orderState.selectedCount(state), loading: false });
    } catch (error) { this.setData({ loading: false, error: error.message || '加载失败' }); }
  },
  changeMeal(event) { if (this.data.pendingOperations.length) { this.setData({ error: '请先重试未提交的点菜' }); return; } const state = orderState.switchMeal(this.data.state, event.detail.value); this.setData({ state, selectedCount: orderState.selectedCount(state) }); this.applyFilters(); },
  onDateChange(event) { if (this.data.pendingOperations.length) { this.setData({ error: '请先重试未提交的点菜' }); return; } this.setData({ state: orderState.changeDate(this.data.state, event.detail.value) }); this.loadData(); },
  chooseCategory(event) { this.setData({ categoryId: event.currentTarget.dataset.id || '' }); this.applyFilters(); },
  onSearch(event) { this.setData({ query: event.detail.value }); this.applyFilters(); },
  applyFilters() { const filtered = orderState.filterDishes(this.data.dishes, { categoryId: this.data.categoryId, query: this.data.query }); this.setData({ visibleDishes: orderState.decorateDishes(filtered, this.data.state) }); },
  async toggleDish(event) {
    if (this.data.pendingOperations.length) { this.setData({ error: '请先重试上次未提交的点菜' }); return; }
    const dishId = event.detail.dish.id;
    const selected = !orderState.selectedIds(this.data.state).includes(dishId);
    const state = orderState.toggleDish(this.data.state, dishId);
    this.setData({ state, selectedCount: orderState.selectedCount(state), pendingDishId: dishId, error: '' }); this.applyFilters();
    const pendingOperations = [{ dishId, selected }];
    try { await orderState.submitOperations(state, pendingOperations, api.request); this.setData({ pendingOperations: [], serverSelectionsByMeal: { ...this.data.serverSelectionsByMeal, [state.mealType]: orderState.selectedIds(state) } }); wx.showToast({ title: selected ? '已加入' : '已取消', icon: 'success' }); }
    catch (error) { this.setData({ pendingOperations, error: `${error.message || '提交失败'}，选择已保留` }); }
    finally { this.setData({ pendingDishId: '' }); }
  },
  async retryPending() {
    if (!this.data.pendingOperations.length) return;
    this.setData({ pendingDishId: this.data.pendingOperations[0].dishId, error: '' });
    try { await orderState.submitOperations(this.data.state, this.data.pendingOperations, api.request); this.setData({ pendingOperations: [], serverSelectionsByMeal: { ...this.data.serverSelectionsByMeal, [this.data.state.mealType]: orderState.selectedIds(this.data.state) } }); wx.showToast({ title: '提交成功', icon: 'success' }); }
    catch (error) { this.setData({ error: error.message || '重试失败' }); }
    finally { this.setData({ pendingDishId: '' }); }
  },
});
