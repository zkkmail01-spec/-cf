const api = require('../../utils/api');
const dishForm = require('../../utils/dish-form');

Page({
  data: { id: '', categories: [], categoryIndex: 0, form: { name: '', categoryId: '', imageFileId: '', description: '', ingredients: [] }, errors: {}, loading: true, saving: false, error: '' },
  async onLoad(options) { this.setData({ id: options.id || '' }); await this.loadForm(); },
  async loadForm() {
    try {
      const [session, categories, dish] = await Promise.all([api.request({ path: '/session' }), api.request({ path: '/categories' }), this.data.id ? api.request({ path: `/dishes/${this.data.id}` }) : Promise.resolve(null)]);
      if (!dishForm.canEditDish(session.member.role)) { wx.showToast({ title: '仅厨师长可编辑', icon: 'none' }); wx.navigateBack(); return; }
      const form = dish || { name: '', categoryId: categories[0] && categories[0].id, imageFileId: '', description: '', ingredients: [] };
      this.setData({ categories, form, categoryIndex: Math.max(0, categories.findIndex((item) => item.id === form.categoryId)), loading: false });
    } catch (error) { this.setData({ loading: false, error: error.message || '加载失败' }); }
  },
  setField(event) { this.setData({ [`form.${event.currentTarget.dataset.field}`]: event.detail.value }); },
  chooseCategory(event) { const categoryIndex = Number(event.detail.value); this.setData({ categoryIndex, 'form.categoryId': this.data.categories[categoryIndex].id }); },
  addIngredient() { this.setData({ 'form.ingredients': [...this.data.form.ingredients, { name: '', quantity: '', unit: '', note: '' }] }); },
  setIngredient(event) { this.setData({ [`form.ingredients[${event.currentTarget.dataset.index}].${event.currentTarget.dataset.field}`]: event.detail.value }); },
  removeIngredient(event) { const ingredients = this.data.form.ingredients.filter((_, index) => index !== Number(event.currentTarget.dataset.index)); this.setData({ 'form.ingredients': ingredients }); },
  chooseImage() {
    wx.chooseMedia({ count: 1, mediaType: ['image'], success: async (result) => {
      try { const form = await dishForm.uploadDishImage(this.data.form, result.tempFiles[0].tempFilePath, api.uploadDishImage); this.setData({ form, error: '' }); }
      catch (error) { this.setData({ error: error.message === 'IMAGE_TOO_LARGE' ? '图片压缩后仍超过 2MB，请选择更小的图片' : '图片上传失败，文字内容已保留，请重试' }); }
    } });
  },
  async save() {
    const errors = dishForm.validateDish(this.data.form); this.setData({ errors }); if (Object.keys(errors).length) return;
    this.setData({ saving: true, error: '' });
    try {
      const payload = { ...this.data.form, ingredients: this.data.form.ingredients.map((item) => ({ ...item, quantity: Number(item.quantity) })) };
      await api.request({ path: this.data.id ? `/dishes/${this.data.id}` : '/dishes', method: this.data.id ? 'PATCH' : 'POST', data: payload, idempotent: true });
      wx.showToast({ title: '已保存', icon: 'success' }); wx.navigateBack();
    } catch (error) { this.setData({ error: error.message || '保存失败' }); }
    finally { this.setData({ saving: false }); }
  },
  deactivate() { wx.showModal({ title: '停用这道菜？', content: '历史菜单仍会保留，菜谱中将不再显示。', success: async (result) => { if (!result.confirm) return; try { await api.request({ path: `/dishes/${this.data.id}`, method: 'DELETE', idempotent: true }); wx.navigateBack(); } catch (error) { this.setData({ error: error.message || '停用失败' }); } } }); },
});
