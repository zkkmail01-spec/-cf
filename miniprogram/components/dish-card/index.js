Component({
  properties: {
    dish: { type: Object, value: {} },
    selected: { type: Boolean, value: false },
    editable: { type: Boolean, value: false },
    loading: { type: Boolean, value: false },
  },
  methods: {
    onTap() { if (!this.data.loading) this.triggerEvent('select', { dish: this.data.dish }); },
    onEdit() { this.triggerEvent('edit', { dish: this.data.dish }); },
  },
});
