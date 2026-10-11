<script setup lang="ts">
defineProps<{ title: string; headingId: string }>();
</script>

<template>
  <section
    class="panel"
    :aria-labelledby="headingId"
  >
    <h2 :id="headingId">
      {{ title }}
    </h2>
    <slot />
  </section>
</template>

<style scoped>
.panel {
  padding: 16px;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 10px;
}

h2 {
  margin: 0 0 12px;
  font-size: 16px;
  font-weight: 600;
}
</style>
