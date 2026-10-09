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
