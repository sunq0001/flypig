<!--
PriceTooltip：模型定价工具提示内容
-->
<template>
  <table class="price-table">
    <tbody>
      <tr>
        <td class="pt-label">
          百万tokens输入（缓存未命中）
        </td>
        <td class="pt-value">
          {{ symbol }} {{ prices?.input?.toFixed(3) }}
        </td>
      </tr>
      <tr v-if="prices?.input_cache_hit != null">
        <td class="pt-label">
          百万tokens输入（缓存命中）
        </td>
        <td class="pt-value">
          {{ symbol }} {{ prices?.input_cache_hit?.toFixed(4) }}
        </td>
      </tr>
      <tr>
        <td class="pt-label">
          百万tokens输出
        </td>
        <td class="pt-value">
          {{ symbol }} {{ prices?.output?.toFixed(3) }}
        </td>
      </tr>
    </tbody>
  </table>
  <div class="pt-date">
    更新于 {{ updateTime }}
  </div>
</template>

<script setup>
defineProps({
  prices: { type: Object, default: null },
  symbol: { type: String, default: '$' },
  updateTime: { type: String, default: '' },
})
</script>

<style scoped>
.price-table { border-collapse: collapse; white-space: nowrap; }
.price-table td { padding: 1px 4px; font-size: 11px; line-height: 1.6; }
.pt-label { color: #999; padding-right: 12px; }
.pt-value { color: #eee; font-weight: 600; font-family: monospace; text-align: right; }
.pt-date { margin-top: 3px; padding-top: 3px; border-top: 1px solid #3a3a3a; color: #666; font-size: 10px; text-align: right; }
</style>
