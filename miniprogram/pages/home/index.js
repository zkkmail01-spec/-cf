const api = require('../../utils/api');

function today() {
  const now = new Date();
  const two = (value) => String(value).padStart(2, '0');
  return `${now.getFullYear()}-${two(now.getMonth() + 1)}-${two(now.getDate())}`;
}

Page({
  data: { date: '', mealType: 'lunch', day: null, frequent: [], loading: true, error: '' },
  onShow() { this.loadHome(); },
  async loadHome() {
    const date = today();
    this.setData({ date, loading: true, error: '' });
    try {
      const [session, day, frequent] = await Promise.all([
        api.request({ path: '/session' }),
        api.request({ path: `/meals/${date}` }),
        api.request({ path: '/dishes/frequent' }),
      ]);
      getApp().globalData.session = session;
      this.setData({ day, frequent, loading: false });
    } catch (error) { this.setData({ loading: false, error: error.message || '加载失败' }); }
  },
  changeMeal(event) { this.setData({ mealType: event.detail.value }); },
  openOrder() { wx.navigateTo({ url: `/pages/order/index?date=${this.data.date}&mealType=${this.data.mealType}` }); },
  openDishes() { wx.switchTab({ url: '/pages/dishes/index' }); },
  openShopping() { wx.navigateTo({ url: '/pages/shopping/index' }); },
  openFamily() { wx.navigateTo({ url: '/pages/family/index' }); },
});
