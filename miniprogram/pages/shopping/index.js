const api = require('../../utils/api');
const { formatLocalDate } = require('../../utils/date');
const records = require('../../utils/records-state');

Page({
  data: { start: '', end: '', items: [], checkedKeys: [], loading: true, saving: false, error: '' },
  onLoad() { const date = formatLocalDate(); this.setData({ start: date, end: date }); this.loadShopping(); },
  onStart(event) { this.setData({ start: event.detail.value }); this.loadShopping(); },
  onEnd(event) { this.setData({ end: event.detail.value }); this.loadShopping(); },
  async loadShopping() {
    this.setData({ loading: true, error: '' });
    try { const result = await api.request({ path: `/shopping?start=${this.data.start}&end=${this.data.end}` }); this.setData({ items: records.decorateShoppingItems(result.items, result.checkedKeys), checkedKeys: result.checkedKeys, loading: false }); }
    catch (error) { this.setData({ loading: false, error: error.message || '采购清单加载失败' }); }
  },
  async toggleItem(event) {
    const checkedKeys = records.toggleCheckedKey(this.data.checkedKeys, event.currentTarget.dataset.key);
    this.setData({ checkedKeys, items: records.decorateShoppingItems(this.data.items, checkedKeys), saving: true, error: '' });
    try { await api.request({ path: '/shopping/checks', method: 'PUT', data: { rangeStart: this.data.start, rangeEnd: this.data.end, checkedKeys }, idempotent: true }); }
    catch (error) { this.setData({ error: error.message || '勾选保存失败' }); }
    finally { this.setData({ saving: false }); }
  },
});
