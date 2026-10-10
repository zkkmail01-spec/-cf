const { CLOUDRUN_SERVICE_NAME } = require('../config/env');

const API_PREFIX = '/api/v1';
const IDEMPOTENCY_STORAGE_PREFIX = 'pending-idempotency:';

class ApiError extends Error {
  constructor(message, { code = 'REQUEST_FAILED', statusCode = 0, details = null } = {}) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.statusCode = statusCode;
    this.details = details;
  }
}

function stableStringify(value) {
  if (value === undefined) return '';
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`;
  return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(',')}}`;
}

function shortHash(value) {
  let hash = 5381;
  for (let index = 0; index < value.length; index += 1) hash = ((hash << 5) + hash) ^ value.charCodeAt(index);
  return (hash >>> 0).toString(36);
}

function operationKey(method, path, data) {
  return `${IDEMPOTENCY_STORAGE_PREFIX}${method}:${path}:${shortHash(stableStringify(data))}`;
}

function createIdempotencyKey() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`;
}

function pendingIdempotencyKey(method, path, data) {
  const storageKey = operationKey(method, path, data);
  let key = wx.getStorageSync(storageKey);
  if (!key) {
    key = createIdempotencyKey();
    wx.setStorageSync(storageKey, key);
  }
  return { key, storageKey };
}

async function request({ path, method = 'GET', data, idempotent = false }) {
  const normalizedMethod = method.toUpperCase();
  const header = {
    'X-WX-SERVICE': CLOUDRUN_SERVICE_NAME,
    'content-type': 'application/json',
  };
  let idempotency = null;

  if (idempotent) {
    idempotency = pendingIdempotencyKey(normalizedMethod, path, data);
    header['Idempotency-Key'] = idempotency.key;
  }

  const response = await wx.cloud.callContainer({
    path: `${API_PREFIX}${path}`,
    method: normalizedMethod,
    header,
    data,
  });

  if (response.statusCode < 200 || response.statusCode >= 300) {
    const envelope = response.data && response.data.error;
    throw new ApiError(
      (envelope && envelope.message) || '请求失败，请稍后重试',
      {
        code: (envelope && envelope.code) || 'REQUEST_FAILED',
        statusCode: response.statusCode,
        details: envelope && envelope.details,
      },
    );
  }

  if (idempotency) {
    wx.removeStorageSync(idempotency.storageKey);
  }
  return response.data;
}

async function uploadDishImage(filePath) {
  const extension = (filePath.split('.').pop() || 'jpg').toLowerCase();
  const result = await wx.cloud.uploadFile({
    cloudPath: `dish-images/${Date.now()}-${Math.random().toString(36).slice(2)}.${extension}`,
    filePath,
  });
  return result.fileID;
}

module.exports = { ApiError, request, uploadDishImage };
