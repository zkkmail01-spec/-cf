beforeEach(() => jest.resetModules());

test('exposes member management controls only to chefs', () => {
  const family = require('../utils/family-state');

  expect(family.permissionsFor('chef')).toEqual({ canInvite: true, canRemoveMembers: true, canEditFamily: true });
  expect(family.permissionsFor('member')).toEqual({ canInvite: false, canRemoveMembers: false, canEditFamily: false });
});

test('decorates member initials before rendering in WXML', () => {
  const { decorateMembers } = require('../utils/family-state');

  expect(decorateMembers([{ id: '1', nickname: '小王' }, { id: '2', nickname: '' }])).toEqual([
    { id: '1', nickname: '小王', initial: '小' },
    { id: '2', nickname: '', initial: '家' },
  ]);
});

test('creates a share path containing only the opaque invitation code', () => {
  const { invitationShare } = require('../utils/family-state');

  expect(invitationShare({ code: 'safe-code-123', familyName: '幸福一家' })).toEqual({
    title: '邀请你加入幸福一家',
    path: '/pages/invite/index?code=safe-code-123',
  });
});

test('maps every invitation failure code to a safe user-facing message', () => {
  const { invitationErrorMessage } = require('../utils/family-state');
  const expected = {
    INVITE_EXPIRED: '邀请已过期，请让厨师长重新邀请',
    INVITE_REVOKED: '邀请已被撤销',
    INVITE_EXHAUSTED: '邀请使用次数已用完',
    ALREADY_IN_FAMILY: '你已加入一个家庭',
    ALREADY_JOINED: '你已经加入这个家庭',
    INVITE_NOT_FOUND: '邀请不存在或已失效',
  };

  Object.entries(expected).forEach(([code, message]) => expect(invitationErrorMessage(code)).toBe(message));
  expect(invitationErrorMessage('INTERNAL_SECRET')).toBe('暂时无法使用这个邀请');
});
