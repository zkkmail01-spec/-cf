const { CLOUDBASE_ENV_ID } = require('./config/env');

App({
  globalData: {
    session: null,
  },

  onLaunch() {
    if (!wx.cloud) {
      wx.showModal({
        title: '微信版本过低',
        content: '请升级微信后再使用家庭点菜。',
        showCancel: false,
      });
      return;
    }
    wx.cloud.init({ env: CLOUDBASE_ENV_ID, traceUser: true });
  },
});
