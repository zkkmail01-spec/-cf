beforeEach(() => jest.resetModules());

test('shows edit controls only to the family chef', () => {
  const form = require('../utils/dish-form');

  expect(form.canEditDish('chef')).toBe(true);
  expect(form.canEditDish('member')).toBe(false);
  expect(form.canEditDish(undefined)).toBe(false);
});

test('rejects zero negative and non-numeric ingredient quantities', () => {
  const { validateDish } = require('../utils/dish-form');
  const base = { name: '番茄炒蛋', categoryId: 'hot', ingredients: [{ name: '鸡蛋', quantity: 2, unit: '个' }] };

  expect(validateDish(base)).toEqual({});
  expect(validateDish({ ...base, ingredients: [{ ...base.ingredients[0], quantity: 0 }] }).ingredients).toBeTruthy();
  expect(validateDish({ ...base, ingredients: [{ ...base.ingredients[0], quantity: -1 }] }).ingredients).toBeTruthy();
  expect(validateDish({ ...base, ingredients: [{ ...base.ingredients[0], quantity: '很多' }] }).ingredients).toBeTruthy();
});

test('assigns uploaded CloudBase file id without changing textual form fields', async () => {
  const { uploadDishImage } = require('../utils/dish-form');
  const form = { name: '酸辣土豆丝', description: '微辣', imageFileId: '' };
  const upload = jest.fn().mockResolvedValue('cloud://demo/potato.jpg');

  const updated = await uploadDishImage(form, 'wxfile://potato.jpg', upload);

  expect(updated).toEqual({ name: '酸辣土豆丝', description: '微辣', imageFileId: 'cloud://demo/potato.jpg' });
  expect(form).toEqual({ name: '酸辣土豆丝', description: '微辣', imageFileId: '' });
});

test('failed image upload preserves the complete form for retry', async () => {
  const { uploadDishImage } = require('../utils/dish-form');
  const form = { name: '酸辣土豆丝', description: '微辣', imageFileId: '', ingredients: [{ name: '土豆' }] };

  await expect(uploadDishImage(form, 'wxfile://potato.jpg', jest.fn().mockRejectedValue(new Error('upload failed'))))
    .rejects.toMatchObject({ message: 'upload failed', form });
});

test('recipe list opens a read-only detail page for ordinary members', () => {
  jest.doMock('../utils/api', () => ({ request: jest.fn() }));
  jest.doMock('../utils/order-state', () => ({ filterDishes: jest.fn() }));
  let definition;
  global.Page = (value) => { definition = value; };
  global.wx = { navigateTo: jest.fn() };
  require('../pages/dishes/index');

  definition.viewDish({ detail: { dish: { id: 'dish-42' } } });

  expect(wx.navigateTo).toHaveBeenCalledWith({ url: '/pages/dish-detail/index?id=dish-42' });
});

test('read-only dish detail loads the complete recipe for family members', async () => {
  const dish = {
    id: 'dish-42',
    name: '番茄炒蛋',
    categoryName: '热菜',
    imageFileId: 'cloud://demo/tomato.jpg',
    description: '鸡蛋炒嫩一些',
    ingredients: [{ id: 'ingredient-1', name: '鸡蛋', quantity: 3, unit: '个', note: '常温' }],
  };
  const request = jest.fn().mockResolvedValue(dish);
  jest.doMock('../utils/api', () => ({ request }));
  let definition;
  global.Page = (value) => { definition = value; };
  global.wx = { setNavigationBarTitle: jest.fn() };
  require('../pages/dish-detail/index');
  const page = { data: { dish: null, loading: true, error: '' }, setData(update) { this.data = { ...this.data, ...update }; } };

  await definition.onLoad.call(page, { id: 'dish-42' });

  expect(request).toHaveBeenCalledWith({ path: '/dishes/dish-42' });
  expect(page.data).toMatchObject({ dish, loading: false, error: '' });
});
