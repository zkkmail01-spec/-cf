const api = require('../../utils/api');

Page({
  data: {
    code: '',
    preview: null,
    nickname: '',
    loading: true,
    submitting: false,
    error: '',
  },

  onLoad(options) {
    const code = options.code || (options.scene && decodeURIComponent(options.scene));
    this.setData({ code: code || '' });
    this.loadPreview();
  },

  async loadPreview() {
    if (!this.data.code) {
      this.setData({ loading: false, error: '邀请链接不完整，请向家人重新获取' });
      return;
    }
    this.setData({ loading: true, error: '' });
    try {
      const preview = await api.request({ path: `/invitations/${encodeURIComponent(this.data.code)}/preview` });
      this.setData({ preview, loading: false });
    } catch (error) {
      this.setData({ loading: false, error: error.message || '邀请已失效' });
    }
  },

  onNickname(event) {
    this.setData({ nickname: event.detail.value });
  },

  async joinFamily() {
    const nickname = this.data.nickname.trim();
    if (!nickname) {
      this.setData({ error: '请填写家人怎么称呼你' });
      return;
    }
    this.setData({ submitting: true, error: '' });
    try {
      await api.request({
        path: `/invitations/${encodeURIComponent(this.data.code)}/join`,
        method: 'POST',
        data: { nickname },
        idempotent: true,
      });
      wx.showToast({ title: '加入成功', icon: 'success' });
      wx.reLaunch({ url: '/pages/home/index' });
    } catch (error) {
      this.setData({ error: error.message || '加入失败，请重试' });
    } finally {
      this.setData({ submitting: false });
    }
  },
});
