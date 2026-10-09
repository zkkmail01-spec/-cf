beforeEach(() => jest.resetModules());

test('formats local calendar dates without UTC timezone drift', () => {
  const { formatLocalDate } = require('../utils/date');
  const localHalfPastMidnight = new Date(2026, 9, 9, 0, 30);

  expect(formatLocalDate(localHalfPastMidnight)).toBe('2026-10-09');
});

test('renders month markers and orders all meals breakfast lunch dinner', () => {
  const records = require('../utils/records-state');
  const grid = records.buildMonthGrid('2026-10', ['2026-10-02', '2026-10-09']);
  const meals = { dinner: { items: ['d'] }, breakfast: { items: ['b'] }, lunch: { items: ['l'] } };

  expect(grid.find((day) => day.date === '2026-10-09')).toMatchObject({ day: 9, hasMeal: true });
  expect(records.orderedMeals(meals).map((meal) => meal.type)).toEqual(['breakfast', 'lunch', 'dinner']);
});

test('builds a repeat request with an explicit target date and meal', () => {
  const { repeatPayload } = require('../utils/records-state');

  expect(repeatPayload('2026-10-09', 'lunch', '2026-10-10', 'dinner')).toEqual({
    sourceDate: '2026-10-09', sourceMealType: 'lunch', targetDate: '2026-10-10', targetMealType: 'dinner',
  });
});

test('toggles shopping item keys while preserving unrelated checks', () => {
  const { toggleCheckedKey } = require('../utils/records-state');

  expect(toggleCheckedKey(['盐|克', '鸡蛋|个'], '盐|克')).toEqual(['鸡蛋|个']);
  expect(toggleCheckedKey(['鸡蛋|个'], '葱|克')).toEqual(['鸡蛋|个', '葱|克']);
});
