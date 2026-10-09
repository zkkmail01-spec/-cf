const api = require('../../utils/api');
const familyState = require('../../utils/family-state');

Page({
  data: { family: null, member: null, members: [], permissions: {}, shareData: null, loading: true, error: '', inviting: false },
  onShow() { this.loadFamily(); },
  async loadFamily() {
    this.setData({ loading: true, error: '' });
    try { const [context, members] = await Promise.all([api.request({ path: '/families/current' }), api.request({ path: '/members' })]); const member = context.currentMember; this.setData({ family: context, member, members: familyState.decorateMembers(members), permissions: familyState.permissionsFor(member.role), loading: false }); }
    catch (error) { this.setData({ loading: false, error: error.message || '家庭信息加载失败' }); }
  },
  async createInvitation() {
    this.setData({ inviting: true, error: '' });
    try { const invitation = await api.request({ path: '/invitations', method: 'POST', data: { expiresInHours: 72, maxUses: 10 }, idempotent: true }); this.setData({ shareData: familyState.invitationShare({ code: invitation.code, familyName: this.data.family.name }) }); wx.showToast({ title: '邀请已生成', icon: 'success' }); }
    catch (error) { this.setData({ error: error.message || '生成邀请失败' }); }
    finally { this.setData({ inviting: false }); }
  },
  onShareAppMessage() { return this.data.shareData || { title: '家里吃什么', path: '/pages/welcome/index' }; },
  removeMember(event) { const member = event.currentTarget.dataset.member; wx.showModal({ title: `移除${member.nickname}？`, content: '对方将无法再查看这个家庭的菜单。', success: async (result) => { if (!result.confirm) return; try { await api.request({ path: `/members/${member.id}`, method: 'DELETE', idempotent: true }); await this.loadFamily(); } catch (error) { this.setData({ error: error.message || '移除失败' }); } } }); },
  leaveFamily() { wx.showModal({ title: '退出家庭？', content: '退出后需要新的邀请才能再加入。', success: async (result) => { if (!result.confirm) return; try { await api.request({ path: '/families/current/leave', method: 'POST', idempotent: true }); wx.reLaunch({ url: '/pages/welcome/index' }); } catch (error) { this.setData({ error: error.message || '退出失败' }); } } }); },
});
