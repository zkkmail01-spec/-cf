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

async function uploadDishImage(form, filePath, upload) {
  try {
    const imageFileId = await upload(filePath);
    return { ...form, imageFileId };
  } catch (error) {
    error.form = form;
    throw error;
  }
}

module.exports = { canEditDish, validateDish, uploadDishImage };
