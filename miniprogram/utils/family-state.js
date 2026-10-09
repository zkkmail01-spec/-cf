const INVITATION_ERRORS = {
  INVITATION_EXPIRED: '邀请已过期，请让厨师长重新邀请',
  INVITATION_REVOKED: '邀请已被撤销',
  INVITATION_EXHAUSTED: '邀请使用次数已用完',
  ALREADY_IN_FAMILY: '你已加入一个家庭',
  INVITATION_NOT_FOUND: '邀请不存在或已失效',
};

function permissionsFor(role) {
  const chef = role === 'chef';
  return { canInvite: chef, canRemoveMembers: chef, canEditFamily: chef };
}

function invitationShare({ code, familyName }) {
  return { title: `邀请你加入${familyName}`, path: `/pages/invite/index?code=${encodeURIComponent(code)}` };
}

function invitationErrorMessage(code) {
  return INVITATION_ERRORS[code] || '暂时无法使用这个邀请';
}

function decorateMembers(members) {
  return members.map((member) => ({ ...member, initial: member.nickname ? member.nickname.slice(0, 1) : '家' }));
}

module.exports = { permissionsFor, invitationShare, invitationErrorMessage, decorateMembers };
