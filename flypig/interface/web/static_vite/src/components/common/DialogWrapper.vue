<!--
DialogWrapper：通用弹窗组件

抽取自 MainLayout（.dlg-*）和 ChatPanel（.ak-*）两处相同的手写弹窗，
消除 ~30 行重复 CSS。

用法：
  <DialogWrapper :show="showDlg" title="标题" @close="showDlg = false">
    <p>弹窗内容</p>
    <template #footer>
      <t-button @click="showDlg = false">取消</t-button>
      <t-button theme="primary" @click="onConfirm">确定</t-button>
    </template>
  </DialogWrapper>
-->
<template>
  <div
    v-if="show"
    class="dlg-overlay"
    @click.self="$emit('close')"
  >
    <div :class="['dlg-box', { 'dlg-box--narrow': narrow }]">
      <div class="dlg-header">
        <span>{{ title }}</span>
        <button
          class="dlg-close"
          @click="$emit('close')"
        >
          ✕
        </button>
      </div>
      <div class="dlg-body">
        <slot />
      </div>
      <div
        v-if="$slots.footer"
        class="dlg-footer"
      >
        <slot name="footer" />
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  show: { type: Boolean, default: false },
  title: { type: String, default: '' },
  narrow: { type: Boolean, default: false },
})
defineEmits(['close'])
</script>

<style scoped>
.dlg-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 3000;
}
.dlg-box {
  background: #252526;
  border: 1px solid #333;
  border-radius: 8px;
  width: 500px;
  max-width: 90vw;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}
.dlg-box--narrow {
  width: 420px;
}
.dlg-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid #333;
  color: #ccc;
  font-size: 14px;
  font-weight: 500;
}
.dlg-close {
  background: none;
  border: none;
  color: #666;
  cursor: pointer;
  font-size: 16px;
  padding: 2px 6px;
  border-radius: 3px;
}
.dlg-close:hover {
  color: #ccc;
  background: #333;
}
.dlg-body {
  padding: 20px;
}
.dlg-footer {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  padding: 12px 20px;
  border-top: 1px solid #333;
}
</style>
