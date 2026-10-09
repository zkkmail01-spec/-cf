const PREFIX = 'meal-draft:';

function keyFor(date, mealType) {
  return `${PREFIX}${date}:${mealType}`;
}

function saveDraft(date, mealType, dishIds) {
  wx.setStorageSync(keyFor(date, mealType), [...dishIds]);
}

function loadDraft(date, mealType) {
  return wx.getStorageSync(keyFor(date, mealType)) || [];
}

function clearDraft(date, mealType) {
  wx.removeStorageSync(keyFor(date, mealType));
}

async function submitDraft(date, mealType, dishIds, submit) {
  saveDraft(date, mealType, dishIds);
  const result = await submit(dishIds);
  clearDraft(date, mealType);
  return result;
}

module.exports = { saveDraft, loadDraft, clearDraft, submitDraft };
