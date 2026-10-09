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
