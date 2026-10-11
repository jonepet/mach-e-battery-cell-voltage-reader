<script setup lang="ts">
defineProps<{ entries: readonly (readonly [term: string, value: string])[] }>();
</script>

<template>
  <dl class="facts">
    <template
      v-for="[term, value] in entries"
      :key="term"
    >
      <dt>{{ term }}</dt>
      <dd>{{ value }}</dd>
    </template>
  </dl>
</template>

<style scoped>
.facts {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, max-content) minmax(150px, 1fr));
  gap: 4px 16px;
  margin: 0 0 12px;
}

dt {
  color: var(--muted);
}

dd {
  margin: 0;
  font-variant-numeric: tabular-nums;
}
</style>
