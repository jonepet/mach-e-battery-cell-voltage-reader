<script setup lang="ts">
import { computed } from 'vue';

import { useGroupHover } from '../composables/useGroupHover';
import { groupDetails } from '../groupDetails';
import type { Reading } from '../types';

const props = defineProps<{ reading: Reading }>();

const { group: hovered, enter, leave, tap } = useGroupHover();

const rows = computed(() =>
  props.reading.voltages.map((_, index) => ({
    ...groupDetails(props.reading, index + 1),
    isOutlier: props.reading.stats?.outliers.includes(index + 1) === true,
  })),
);
</script>

<template>
  <table class="cell-table">
    <thead>
      <tr>
        <th scope="col">
          Cell
        </th>
        <th scope="col">
          Voltage
        </th>
        <th scope="col">
          From median
        </th>
        <th scope="col">
          Capacity
        </th>
        <th scope="col">
          Health
        </th>
        <th scope="col">
          Balancing
        </th>
      </tr>
    </thead>
    <tbody @pointerleave="leave">
      <tr
        v-for="row in rows"
        :key="row.group"
        :class="{ 'row--outlier': row.isOutlier, 'row--hovered': hovered === row.group }"
        @pointerenter="enter(row.group, $event)"
        @pointerup="tap(row.group, $event)"
      >
        <td>{{ row.group }}</td>
        <td>{{ row.voltage ?? 'No value' }}</td>
        <td>{{ row.fromMedian }}</td>
        <td>{{ row.capacity }}</td>
        <td>{{ row.health }}</td>
        <td>{{ row.balancing }}</td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
.cell-table {
  border-collapse: collapse;
  margin-top: 8px;
  font-variant-numeric: tabular-nums;
}

th,
td {
  padding: 2px 16px 2px 0;
  text-align: right;
}

.row--outlier {
  color: var(--error);
}

.row--hovered {
  background: color-mix(in srgb, var(--hover) 22%, transparent);
  box-shadow: inset 3px 0 0 var(--hover);
}
</style>
