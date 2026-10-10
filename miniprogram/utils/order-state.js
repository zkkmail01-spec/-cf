const drafts = require('./meal-draft');

const MEAL_TYPES = ['breakfast', 'lunch', 'dinner'];

function createOrderState({ date = '', mealType = 'breakfast', selectionsByMeal } = {}) {
  return {
    date,
    mealType: MEAL_TYPES.includes(mealType) ? mealType : 'breakfast',
    selectionsByMeal: selectionsByMeal || { breakfast: [], lunch: [], dinner: [] },
  };
}

function switchMeal(state, mealType) {
  if (!MEAL_TYPES.includes(mealType)) return state;
  return { ...state, mealType };
}

function changeDate(state, date) {
  return { ...state, date };
}

function selectedIds(state) {
  return state.selectionsByMeal[state.mealType] || [];
}

function selectedCount(state) {
  return selectedIds(state).length;
}

function toggleDish(state, dishId) {
  const current = selectedIds(state);
  const next = current.includes(dishId)
    ? current.filter((id) => id !== dishId)
    : [...current, dishId];
  return {
    ...state,
    selectionsByMeal: { ...state.selectionsByMeal, [state.mealType]: next },
  };
}

function filterDishes(dishes, { categoryId = '', query = '' } = {}) {
  const needle = query.trim().toLocaleLowerCase();
  return dishes.filter((dish) => {
    if (categoryId && dish.categoryId !== categoryId) return false;
    if (!needle) return true;
    const ingredientNames = (dish.ingredients || []).map((item) => item.name).join(' ');
    return `${dish.name} ${ingredientNames}`.toLocaleLowerCase().includes(needle);
  });
}

function decorateDishes(dishes, state) {
  const selected = selectedIds(state);
  return dishes.map((dish) => ({ ...dish, selected: selected.includes(dish.id) }));
}

function pendingOperations(serverIds, draftIds) {
  return [
    ...draftIds.filter((id) => !serverIds.includes(id)).map((dishId) => ({ dishId, selected: true })),
    ...serverIds.filter((id) => !draftIds.includes(id)).map((dishId) => ({ dishId, selected: false })),
  ];
}

async function submitOperations(state, operations, request) {
  drafts.saveDraft(state.date, state.mealType, selectedIds(state));
  for (const operation of operations) {
    await request({
      path: `/meals/${state.date}/${state.mealType}/selections/${operation.dishId}`,
      method: operation.selected ? 'PUT' : 'DELETE',
      idempotent: true,
    });
  }
  drafts.clearDraft(state.date, state.mealType);
}

async function submitDish(state, dishId, selected, request) {
  return submitOperations(state, [{ dishId, selected }], request);
}

module.exports = {
  MEAL_TYPES,
  createOrderState,
  switchMeal,
  changeDate,
  selectedIds,
  selectedCount,
  toggleDish,
  filterDishes,
  decorateDishes,
  pendingOperations,
  submitOperations,
  submitDish,
};
