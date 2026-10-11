const api = require('../../utils/api');
const { invitationErrorMessage } = require('../../utils/family-state');

Page({
  data: {
    code: '',
    preview: null,
    nickname: '',
    avatarUrl: '',
    loading: true,
    submitting: false,
    error: '',
  },

  onLoad(options) {
    const profile = wx.getStorageSync('wechat-profile');
    if (profile) this.setData({ nickname: profile.nickName || '', avatarUrl: profile.avatarUrl || '' });
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
      this.setData({ loading: false, error: invitationErrorMessage(error.code) });
    }
  },

  onNickname(event) {
    this.setData({ nickname: event.detail.value });
  },

  getWechatProfile() {
    wx.getUserProfile({
      desc: '用于显示家庭成员头像和昵称',
      success: ({ userInfo }) => { wx.setStorageSync('wechat-profile', userInfo); this.setData({ nickname: userInfo.nickName || this.data.nickname, avatarUrl: userInfo.avatarUrl || '' }); },
      fail: () => this.setData({ error: '你可以手动填写昵称，也可以重新点击授权' }),
    });
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
        data: { nickname, avatarUrl: this.data.avatarUrl || null },
        idempotent: true,
      });
      wx.showToast({ title: '加入成功', icon: 'success' });
      wx.reLaunch({ url: '/pages/home/index' });
    } catch (error) {
      this.setData({ error: invitationErrorMessage(error.code) });
    } finally {
      this.setData({ submitting: false });
    }
  },
});
