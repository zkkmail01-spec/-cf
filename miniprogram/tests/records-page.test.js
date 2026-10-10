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

test('records tab refreshes calendar and selected day whenever it becomes visible', () => {
  jest.doMock('../utils/api', () => ({ request: jest.fn() }));
  let definition;
  global.Page = (value) => { definition = value; };
  require('../pages/records/index');
  const page = {
    ...definition,
    data: { ...definition.data, selectedDate: '2026-10-10' },
    loadMonth: jest.fn(),
    loadDay: jest.fn(),
  };

  page.onShow();

  expect(page.loadMonth).toHaveBeenCalledTimes(1);
  expect(page.loadDay).toHaveBeenCalledWith('2026-10-10');
});

test('failed day refresh clears stale meals and exposes retryable error state', async () => {
  const request = jest.fn().mockRejectedValue(new Error('offline'));
  jest.doMock('../utils/api', () => ({ request }));
  let definition;
  global.Page = (value) => { definition = value; };
  require('../pages/records/index');
  const page = {
    ...definition,
    data: { ...definition.data, meals: [{ type: 'lunch', items: ['stale'] }] },
    setData(update) { this.data = { ...this.data, ...update }; },
  };

  await page.loadDay('2026-10-10');

  expect(page.data.meals).toEqual([]);
  expect(page.data.error).toBe('offline');
});

test('a slow previous month response cannot overwrite the current calendar', async () => {
  let resolveOctober;
  let resolveNovember;
  const october = new Promise((resolve) => { resolveOctober = resolve; });
  const november = new Promise((resolve) => { resolveNovember = resolve; });
  const request = jest.fn()
    .mockReturnValueOnce(october)
    .mockReturnValueOnce(november);
  jest.doMock('../utils/api', () => ({ request }));
  let definition;
  global.Page = (value) => { definition = value; };
  require('../pages/records/index');
  const page = {
    ...definition,
    data: { ...definition.data, month: '2026-10' },
    setData(update) { this.data = { ...this.data, ...update }; },
  };

  const first = page.loadMonth();
  page.data.month = '2026-11';
  const second = page.loadMonth();
  resolveNovember({ dates: ['2026-11-08'] });
  await second;
  resolveOctober({ dates: ['2026-10-03'] });
  await first;

  expect(page.data.calendarDays.find((day) => day.date === '2026-11-08')).toMatchObject({ hasMeal: true });
});
