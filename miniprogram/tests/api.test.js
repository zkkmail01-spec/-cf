const storage = new Map();

function installWx(callContainer) {
  global.wx = {
    cloud: {
      callContainer,
      uploadFile: jest.fn().mockResolvedValue({ fileID: 'cloud://demo/dish.jpg' }),
    },
    getStorageSync: jest.fn((key) => storage.get(key)),
    setStorageSync: jest.fn((key, value) => storage.set(key, value)),
    removeStorageSync: jest.fn((key) => storage.delete(key)),
  };
}

beforeEach(() => {
  storage.clear();
  jest.resetModules();
});

test('calls Cloud Hosting with API prefix and service header', async () => {
  const callContainer = jest.fn().mockResolvedValue({ statusCode: 200, data: { ok: true } });
  installWx(callContainer);
  const api = require('../utils/api');

  const result = await api.request({ path: '/session' });

  expect(result).toEqual({ ok: true });
  expect(callContainer).toHaveBeenCalledWith(expect.objectContaining({
    path: '/api/v1/session',
    method: 'GET',
    header: expect.objectContaining({ 'X-WX-SERVICE': 'family-menu-api' }),
  }));
});

test('maps backend error envelopes to ApiError', async () => {
  installWx(jest.fn().mockResolvedValue({
    statusCode: 403,
    data: { error: { code: 'CHEF_REQUIRED', message: '只有厨师长可以操作' } },
  }));
  const api = require('../utils/api');

  await expect(api.request({ path: '/categories' })).rejects.toMatchObject({
    code: 'CHEF_REQUIRED',
    message: '只有厨师长可以操作',
    statusCode: 403,
  });
});

test('reuses pending idempotency key after network failure and clears it after success', async () => {
  const callContainer = jest.fn()
    .mockRejectedValueOnce(new Error('offline'))
    .mockResolvedValueOnce({ statusCode: 200, data: { saved: true } });
  installWx(callContainer);
  const api = require('../utils/api');
  const options = { path: '/meals/2026-10-09/lunch/selections/dish-1', method: 'PUT', idempotent: true };

  await expect(api.request(options)).rejects.toThrow('offline');
  const firstKey = callContainer.mock.calls[0][0].header['Idempotency-Key'];
  const result = await api.request(options);
  const secondKey = callContainer.mock.calls[1][0].header['Idempotency-Key'];

  expect(result).toEqual({ saved: true });
  expect(secondKey).toBe(firstKey);
  expect(storage.size).toBe(0);
});

test('uses different idempotency keys for different payloads on the same route', async () => {
  const callContainer = jest.fn()
    .mockRejectedValueOnce(new Error('offline'))
    .mockResolvedValueOnce({ statusCode: 200, data: { saved: 'second' } })
    .mockResolvedValueOnce({ statusCode: 200, data: { saved: 'first' } });
  installWx(callContainer);
  const api = require('../utils/api');
  const first = { path: '/shopping/checks', method: 'PUT', data: { checkedKeys: ['盐|克'] }, idempotent: true };
  const second = { path: '/shopping/checks', method: 'PUT', data: { checkedKeys: ['鸡蛋|个'] }, idempotent: true };

  await expect(api.request(first)).rejects.toThrow('offline');
  await api.request(second);
  await api.request(first);

  const keys = callContainer.mock.calls.map((call) => call[0].header['Idempotency-Key']);
  expect(keys[1]).not.toBe(keys[0]);
  expect(keys[2]).toBe(keys[0]);
  expect(storage.size).toBe(0);
});

test('configuration never exports an AppSecret', () => {
  installWx(jest.fn());
  const env = require('../config/env');

  expect(env.CLOUDBASE_ENV_ID).toBe('zkk-20261010-d6gfxxdhfe3f8fc75');
  expect(env.CLOUDRUN_SERVICE_NAME).toBe('family-menu-api');
  expect(Object.keys(env).some((key) => /secret/i.test(key))).toBe(false);
});
