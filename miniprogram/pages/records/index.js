const api = require('../../utils/api');
const dates = require('../../utils/date');
const records = require('../../utils/records-state');

Page({
  data: { month: '', calendarDays: [], selectedDate: '', meals: [], loading: true, error: '', repeatSource: null, targetDate: '', targetMealType: 'lunch', repeating: false },
  onLoad() { const selectedDate = dates.formatLocalDate(); this.setData({ month: selectedDate.slice(0, 7), selectedDate, targetDate: selectedDate }); this.loadMonth(); this.loadDay(selectedDate); },
  async loadMonth() {
    try { const result = await api.request({ path: `/meals/calendar?month=${this.data.month}` }); this.setData({ calendarDays: records.buildMonthGrid(this.data.month, result.dates) }); }
    catch (error) { this.setData({ error: error.message || '日历加载失败' }); }
  },
  previousMonth() { this.setData({ month: dates.shiftMonth(this.data.month, -1) }); this.loadMonth(); },
  nextMonth() { this.setData({ month: dates.shiftMonth(this.data.month, 1) }); this.loadMonth(); },
  selectDay(event) { const date = event.currentTarget.dataset.date; if (!date) return; this.setData({ selectedDate: date, targetDate: date }); this.loadDay(date); },
  async loadDay(date) {
    this.setData({ loading: true, error: '' });
    try { const day = await api.request({ path: `/meals/${date}` }); this.setData({ meals: records.orderedMeals(day.meals), loading: false }); }
    catch (error) { this.setData({ loading: false, error: error.message || '记录加载失败' }); }
  },
  openRepeat(event) { this.setData({ repeatSource: { date: this.data.selectedDate, mealType: event.currentTarget.dataset.meal }, targetDate: dates.formatLocalDate(), targetMealType: event.currentTarget.dataset.meal }); },
  closeRepeat() { this.setData({ repeatSource: null }); },
  onTargetDate(event) { this.setData({ targetDate: event.detail.value }); },
  chooseTargetMeal(event) { this.setData({ targetMealType: event.currentTarget.dataset.meal }); },
  async repeatMeal() {
    this.setData({ repeating: true, error: '' });
    try { await api.request({ path: '/meals/repeat', method: 'POST', data: records.repeatPayload(this.data.repeatSource.date, this.data.repeatSource.mealType, this.data.targetDate, this.data.targetMealType), idempotent: true }); wx.showToast({ title: '已加入目标餐次', icon: 'success' }); this.setData({ repeatSource: null }); }
    catch (error) { this.setData({ error: error.message || '再次点菜失败' }); }
    finally { this.setData({ repeating: false }); }
  },
});
