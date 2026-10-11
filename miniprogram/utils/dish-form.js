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
  return new Promise((resolve, reject) => {
    if (typeof wx === 'undefined' || typeof wx.compressImage !== 'function') return resolve(filePath);
    wx.compressImage({ src: filePath, quality: 75, success: (result) => resolve(result.tempFilePath), fail: reject });
  });
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
