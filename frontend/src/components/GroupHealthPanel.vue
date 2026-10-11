<script setup lang="ts">
import { computed } from 'vue';

import { ampereHours, percent } from '../format';
import type { Reading } from '../types';
import DeviationChart from './DeviationChart.vue';
import FactList from './FactList.vue';
import PanelSection from './PanelSection.vue';
import PanelWarning from './PanelWarning.vue';

const props = defineProps<{ reading: Reading | null }>();

const health = computed(() => props.reading?.health);
const packHealthChartCenter = computed(() => {
  const packHealth = props.reading?.signals.find((signal) => signal.key === 'soh');
  return health.value?.reference_capacity === null || packHealth === undefined ? null : packHealth.value;
});

const facts = computed(() => {
  const current = health.value;
  if (!current) {
    return [];
  }
  const healthOf = (group: number): string =>
    current.reference_capacity === null ? '' : `, ${percent(current.health[group - 1] ?? 0)}`;
  return [
    ['Capacity at 100 %', current.reference_capacity === null ? 'Not available' : ampereHours(current.reference_capacity)],
    ['Weakest', `${ampereHours(current.minimum)}${healthOf(current.weakest_group)} (#${current.weakest_group})`],
    ['Strongest', `${ampereHours(current.maximum)}${healthOf(current.strongest_group)} (#${current.strongest_group})`],
    ['Mean', ampereHours(current.mean)],
    ['Spread', ampereHours(current.maximum - current.minimum)],
  ] as const;
});

const weakest = computed(() => new Set(health.value ? [health.value.weakest_group] : []));
</script>

<template>
  <PanelSection
    title="Cell group health"
    heading-id="health-heading"
  >
    <PanelWarning v-if="reading?.health_error">
      The cell group capacities could not be read.
    </PanelWarning>
    <FactList :entries="facts" />
    <DeviationChart
      v-if="health"
      chart-id="health-chart"
      label="State of health of each cell group relative to the pack"
      :values="health.health"
      :center="packHealthChartCenter"
      unit="%"
      :minimum-extent="0.5"
      :highlighted="weakest"
      highlight-class="outlier"
    >
      State of health of each cell group relative to the pack, in percentage points: group capacity divided by
      the pack capacity at 100 %. Hover a bar for its value.
    </DeviationChart>
  </PanelSection>
</template>
