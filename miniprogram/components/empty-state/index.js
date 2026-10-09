Component({
  properties: {
    loading: { type: Boolean, value: false },
    error: { type: String, value: '' },
    title: { type: String, value: '这里还没有内容' },
    actionText: { type: String, value: '' },
  },
  methods: { onAction() { this.triggerEvent('action'); } },
});
