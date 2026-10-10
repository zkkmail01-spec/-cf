const storage = new Map();

beforeEach(() => {
  storage.clear();
  global.wx = {
    getStorageSync: jest.fn((key) => storage.get(key)),
    setStorageSync: jest.fn((key, value) => storage.set(key, value)),
    removeStorageSync: jest.fn((key) => storage.delete(key)),
  };
  jest.resetModules();
});

test('switches among breakfast lunch and dinner without losing selections', () => {
  const state = require('../utils/order-state');
  let order = state.createOrderState();

  order = state.toggleDish(order, 'dish-breakfast');
  order = state.switchMeal(order, 'lunch');
  order = state.toggleDish(order, 'dish-lunch');
  order = state.switchMeal(order, 'breakfast');

  expect(order.mealType).toBe('breakfast');
  expect(state.selectedIds(order)).toEqual(['dish-breakfast']);
  expect(state.selectedCount(order)).toBe(1);
});

test('filters dishes by category and a case-insensitive search term', () => {
  const { filterDishes } = require('../utils/order-state');
  const dishes = [
    { id: '1', categoryId: 'hot', name: '番茄炒蛋', ingredients: [{ name: '鸡蛋' }] },
    { id: '2', categoryId: 'cold', name: 'Cucumber Salad', ingredients: [{ name: '黄瓜' }] },
  ];

  expect(filterDishes(dishes, { categoryId: 'hot', query: '' }).map((dish) => dish.id)).toEqual(['1']);
  expect(filterDishes(dishes, { categoryId: '', query: 'cucumber' }).map((dish) => dish.id)).toEqual(['2']);
  expect(filterDishes(dishes, { categoryId: '', query: '鸡蛋' }).map((dish) => dish.id)).toEqual(['1']);
});

test('decorates visible dishes with template-safe selected flags', () => {
  const state = require('../utils/order-state');
  const order = state.toggleDish(state.createOrderState(), 'dish-2');

  expect(state.decorateDishes([{ id: 'dish-1' }, { id: 'dish-2' }], order)).toEqual([
    { id: 'dish-1', selected: false },
    { id: 'dish-2', selected: true },
  ]);
});

test('keeps the active meal draft after an incremental request fails', async () => {
  const state = require('../utils/order-state');
  const failingRequest = jest.fn().mockRejectedValue(new Error('offline'));
  const order = state.toggleDish(state.createOrderState({ date: '2026-10-09', mealType: 'dinner' }), 'dish-1');

  await expect(state.submitDish(order, 'dish-1', true, failingRequest)).rejects.toThrow('offline');

  expect(wx.getStorageSync('meal-draft:2026-10-09:dinner')).toEqual(['dish-1']);
  expect(failingRequest).toHaveBeenCalledWith(expect.objectContaining({
    path: '/meals/2026-10-09/dinner/selections/dish-1',
    method: 'PUT',
    idempotent: true,
  }));
});

test('changes ordering date without dropping other meal selections', () => {
  const state = require('../utils/order-state');
  const order = state.toggleDish(state.createOrderState({ date: '2026-10-10', mealType: 'lunch' }), 'dish-1');

  const changed = state.changeDate(order, '2026-10-11');

  expect(changed.date).toBe('2026-10-11');
  expect(state.selectedIds(changed)).toEqual(['dish-1']);
});

test('derives exact pending operations and retries the same direction', async () => {
  const state = require('../utils/order-state');
  const order = state.createOrderState({
    date: '2026-10-10',
    mealType: 'lunch',
    selectionsByMeal: { breakfast: [], lunch: ['kept', 'added'], dinner: [] },
  });
  const operations = state.pendingOperations(['kept', 'removed'], ['kept', 'added']);
  const request = jest.fn()
    .mockRejectedValueOnce(new Error('offline'))
    .mockResolvedValue({ ok: true });

  expect(operations).toEqual([
    { dishId: 'added', selected: true },
    { dishId: 'removed', selected: false },
  ]);
  await expect(state.submitOperations(order, operations, request)).rejects.toThrow('offline');
  await state.submitOperations(order, operations, request);

  expect(request.mock.calls.map((call) => call[0].method)).toEqual(['PUT', 'PUT', 'DELETE']);
  expect(wx.getStorageSync('meal-draft:2026-10-10:lunch')).toBeUndefined();
});

test('order page retry resubmits the failed action instead of toggling it', async () => {
  const request = jest.fn()
    .mockRejectedValueOnce(new Error('offline'))
    .mockResolvedValueOnce({ ok: true });
  jest.doMock('../utils/api', () => ({ request }));
  let definition;
  global.Page = (value) => { definition = value; };
  global.getApp = () => ({ globalData: { session: { identity: { openid: 'me' } } } });
  global.wx.showToast = jest.fn();
  require('../pages/order/index');
  const page = {
    ...definition,
    data: {
      ...definition.data,
      state: require('../utils/order-state').createOrderState({ date: '2026-10-10', mealType: 'lunch' }),
      dishes: [{ id: 'dish-1' }],
      visibleDishes: [{ id: 'dish-1', selected: false }],
    },
    setData(update) { this.data = { ...this.data, ...update }; },
  };

  await page.toggleDish({ detail: { dish: { id: 'dish-1' } } });
  await page.retryPending();

  expect(request.mock.calls.map((call) => call[0].method)).toEqual(['PUT', 'PUT']);
});
