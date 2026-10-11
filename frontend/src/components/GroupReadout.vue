<script setup lang="ts">
import { computed } from 'vue';

import { useGroupHover } from '../composables/useGroupHover';
import { groupDetails } from '../groupDetails';
import type { Reading } from '../types';

const props = defineProps<{ reading: Reading | null }>();

const { group } = useGroupHover();

const details = computed(() =>
  props.reading && group.value !== null ? groupDetails(props.reading, group.value) : null,
);

const entries = computed(() =>
  details.value
    ? ([
        ['Voltage', details.value.voltage],
        ['From median', details.value.fromMedian],
        ['Capacity', details.value.capacity],
        ['Health', details.value.health],
        ['State of charge', details.value.charge],
        ['Balancing', details.value.balancing],
      ] as const)
    : [],
);
</script>

<template>
  <aside
    class="readout"
    aria-live="off"
  >
    <template v-if="details">
      <strong>Cell group #{{ details.group }}</strong>
      <dl>
        <div
          v-for="[term, value] in entries"
          :key="term"
        >
          <dt>{{ term }}</dt>
          <dd>{{ value ?? '—' }}</dd>
        </div>
      </dl>
    </template>
    <span
      v-else
      class="readout__hint"
    >Hover a cell group in a chart or the table to see its values.</span>
  </aside>
</template>

<style scoped>
.readout {
  position: sticky;
  bottom: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 4px 24px;
  min-height: 48px;
  padding: 10px 16px;
  background: var(--panel);
  border-top: 2px solid var(--hover);
}

dl {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 24px;
  margin: 0;
}

dl div {
  display: flex;
  gap: 6px;
}

dt {
  color: var(--muted);
}

dd {
  margin: 0;
  font-variant-numeric: tabular-nums;
}

.readout__hint {
  color: var(--muted);
}
</style>
