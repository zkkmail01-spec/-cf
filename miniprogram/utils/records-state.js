const MEAL_LABELS = { breakfast: '早餐', lunch: '午餐', dinner: '晚餐' };

function buildMonthGrid(month, markedDates = []) {
  const [year, monthNumber] = month.split('-').map(Number);
  const count = new Date(year, monthNumber, 0).getDate();
  const leading = new Date(year, monthNumber - 1, 1).getDay();
  const marks = new Set(markedDates);
  const grid = Array.from({ length: leading }, (_, index) => ({ key: `empty-${index}`, empty: true }));
  for (let day = 1; day <= count; day += 1) {
    const date = `${month}-${String(day).padStart(2, '0')}`;
    grid.push({ key: date, date, day, hasMeal: marks.has(date), empty: false });
  }
  return grid;
}

function orderedMeals(meals = {}) {
  return ['breakfast', 'lunch', 'dinner'].map((type) => ({
    type,
    label: MEAL_LABELS[type],
    ...(meals[type] || { items: [], version: 0 }),
  }));
}

function repeatPayload(sourceDate, sourceMealType, targetDate, targetMealType) {
  return { sourceDate, sourceMealType, targetDate, targetMealType };
}

function toggleCheckedKey(checkedKeys, key) {
  return checkedKeys.includes(key) ? checkedKeys.filter((item) => item !== key) : [...checkedKeys, key];
}

function decorateShoppingItems(items, checkedKeys) {
  return items.map((item) => ({ ...item, checked: checkedKeys.includes(item.key) }));
}

module.exports = { buildMonthGrid, orderedMeals, repeatPayload, toggleCheckedKey, decorateShoppingItems };
