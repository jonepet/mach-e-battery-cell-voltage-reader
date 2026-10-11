<template>
  <p class="warning">
    <slot />
  </p>
</template>

<style scoped>
.warning {
  padding: 8px 12px;
  background: var(--warning-bg);
  border: 1px solid var(--warning-border);
  border-radius: 6px;
}
</style>
