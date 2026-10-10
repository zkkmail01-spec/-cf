const api = require('../../utils/api');

Page({
  data: { dish: null, loading: true, error: '' },
  async onLoad(options) {
    const id = options && options.id;
    if (!id) {
      this.setData({ loading: false, error: '缺少菜品信息' });
      return;
    }
    this.setData({ loading: true, error: '' });
    try {
      const dish = await api.request({ path: `/dishes/${id}` });
      this.setData({ dish, loading: false, error: '' });
      wx.setNavigationBarTitle({ title: dish.name || '菜品详情' });
    } catch (error) {
      this.setData({ dish: null, loading: false, error: error.message || '菜品加载失败' });
    }
  },
});
