function canEditDish(role) {
  return role === 'chef';
}

function validateDish(form) {
  const errors = {};
  if (!form.name || !form.name.trim()) errors.name = '请输入菜品名称';
  if (!form.categoryId) errors.categoryId = '请选择分类';
  const invalidIngredient = (form.ingredients || []).some((item) => (
    !item.name || !item.name.trim()
    || !item.unit || !item.unit.trim()
    || !Number.isFinite(Number(item.quantity))
    || Number(item.quantity) <= 0
  ));
  if (invalidIngredient) errors.ingredients = '食材名称、正数数量和单位都要填写';
  return errors;
}

function compressImage(filePath) {
  const limit = 2 * 1024 * 1024;
  if (typeof wx === 'undefined' || typeof wx.compressImage !== 'function') return Promise.resolve(filePath);
  const fileSize = (path) => new Promise((resolve, reject) => wx.getFileInfo({ filePath: path, success: (result) => resolve(result.size), fail: reject }));
  return (async () => {
    let currentPath = filePath;
    let size = await fileSize(currentPath);
    for (const quality of [80, 60, 40, 20]) {
      if (size <= limit) return currentPath;
      currentPath = await new Promise((resolve, reject) => wx.compressImage({ src: currentPath, quality, success: (result) => resolve(result.tempFilePath), fail: reject }));
      size = await fileSize(currentPath);
    }
    if (size > limit) throw new Error('IMAGE_TOO_LARGE');
    return currentPath;
  })();
}

async function uploadDishImage(form, filePath, upload) {
  try {
    const compressedPath = await compressImage(filePath);
    const imageFileId = await upload(compressedPath);
    return { ...form, imageFileId };
  } catch (error) {
    error.form = form;
    throw error;
  }
}

module.exports = { canEditDish, validateDish, compressImage, uploadDishImage };
