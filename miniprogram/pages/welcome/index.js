const api = require('../../utils/api');

Page({
  data: {
    loading: true,
    submitting: false,
    error: '',
    familyName: '',
    nickname: '',
    inviteCode: '',
  },

  onLoad(options) {
    const code = options.code || (options.scene && decodeURIComponent(options.scene));
    if (code) {
      wx.redirectTo({ url: `/pages/invite/index?code=${encodeURIComponent(code)}` });
      return;
    }
    this.loadSession();
  },

  async loadSession() {
    this.setData({ loading: true, error: '' });
    try {
      const session = await api.request({ path: '/session' });
      getApp().globalData.session = session;
      if (session.family && session.member) {
        wx.reLaunch({ url: '/pages/home/index' });
        return;
      }
      this.setData({ loading: false });
    } catch (error) {
      this.setData({ loading: false, error: error.message || '暂时无法连接，请重试' });
    }
  },

  onFamilyName(event) {
    this.setData({ familyName: event.detail.value });
  },

  onNickname(event) {
    this.setData({ nickname: event.detail.value });
  },

  onInviteCode(event) {
    this.setData({ inviteCode: event.detail.value.trim() });
  },

  async createFamily() {
    const familyName = this.data.familyName.trim();
    const nickname = this.data.nickname.trim();
    if (!familyName || !nickname) {
      this.setData({ error: '请填写家庭名称和你的称呼' });
      return;
    }
    this.setData({ submitting: true, error: '' });
    try {
      await api.request({
        path: '/families',
        method: 'POST',
        data: { name: familyName, nickname },
        idempotent: true,
      });
      wx.reLaunch({ url: '/pages/home/index' });
    } catch (error) {
      this.setData({ error: error.message || '创建失败，请重试' });
    } finally {
      this.setData({ submitting: false });
    }
  },

  openInvite() {
    if (!this.data.inviteCode) {
      this.setData({ error: '请输入邀请码' });
      return;
    }
    wx.navigateTo({ url: `/pages/invite/index?code=${encodeURIComponent(this.data.inviteCode)}` });
  },
});
