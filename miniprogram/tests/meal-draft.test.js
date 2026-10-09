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

test('stores and restores a meal draft by date and meal type', () => {
  const drafts = require('../utils/meal-draft');
  const selection = ['dish-1', 'dish-2'];

  drafts.saveDraft('2026-10-09', 'lunch', selection);

  expect(drafts.loadDraft('2026-10-09', 'lunch')).toEqual(selection);
  expect(drafts.loadDraft('2026-10-09', 'dinner')).toEqual([]);
});

test('keeps draft after submit failure and clears only after success', async () => {
  const drafts = require('../utils/meal-draft');
  const selection = ['dish-1'];
  const failedSubmit = jest.fn().mockRejectedValue(new Error('offline'));

  await expect(
    drafts.submitDraft('2026-10-09', 'lunch', selection, failedSubmit),
  ).rejects.toThrow('offline');
  expect(drafts.loadDraft('2026-10-09', 'lunch')).toEqual(selection);

  await drafts.submitDraft(
    '2026-10-09',
    'lunch',
    selection,
    jest.fn().mockResolvedValue({ ok: true }),
  );
  expect(drafts.loadDraft('2026-10-09', 'lunch')).toEqual([]);
});
