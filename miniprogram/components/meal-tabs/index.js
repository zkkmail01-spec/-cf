Component({
  properties: { value: { type: String, value: 'breakfast' } },
  data: { tabs: [{ value: 'breakfast', label: '早餐' }, { value: 'lunch', label: '午餐' }, { value: 'dinner', label: '晚餐' }] },
  methods: { onChange(event) { this.triggerEvent('change', { value: event.currentTarget.dataset.value }); } },
});
