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

function operationKey(method, path) {
  return `${IDEMPOTENCY_STORAGE_PREFIX}${method}:${path}`;
}

function createIdempotencyKey() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`;
}

function pendingIdempotencyKey(method, path) {
  const storageKey = operationKey(method, path);
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
    idempotency = pendingIdempotencyKey(normalizedMethod, path);
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
