<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import { useNow } from '../composables/useNow';
import { duration, elapsed, millivolts } from '../format';
import type { Reading } from '../types';
import CellTable from './CellTable.vue';
import DeviationChart from './DeviationChart.vue';
import FactList from './FactList.vue';
import PanelSection from './PanelSection.vue';
import PanelWarning from './PanelWarning.vue';

const props = defineProps<{ reading: Reading | null }>();

const now = useNow(1000);
const receivedAt = ref(Date.now());
watch(
  () => props.reading?.timestamp,
  () => {
    receivedAt.value = Date.now();
  },
);

const measuredAgo = computed(() => {
  const age = props.reading ? props.reading.voltages_age_s : null;
  return age === null ? null : age + Math.max(0, now.value - receivedAt.value) / 1000;
});

const facts = computed(() => {
  const reading = props.reading;
  if (!reading?.stats) {
    return [];
  }
  const { stats, voltages, balancing } = reading;
  const outliers = stats.outliers.length ? stats.outliers.map((cell) => `#${cell}`).join(', ') : 'None';
  const balancingFacts = balancing
    ? ([
        ['Groups balancing', `${balancing.active_count} / ${balancing.active.length}`],
        ['Longest running', balancing.active_count ? duration(balancing.longest_s) : '—'],
      ] as const)
    : [];
  return [
    ['Readings', `${stats.valid} / ${voltages.length}`],
    ['Minimum', `${stats.minimum.toFixed(4)} V (#${stats.min_cell})`],
    ['Maximum', `${stats.maximum.toFixed(4)} V (#${stats.max_cell})`],
    ['Mean', `${stats.mean.toFixed(4)} V`],
    ['Spread', `${millivolts(stats.spread)}${stats.spread_exceeded ? ' — above warning limit' : ''}`],
    ['Std. deviation', millivolts(stats.stdev)],
    ['Outliers', outliers],
    ...balancingFacts,
  ] as const;
});

const millivoltValues = computed(
  () => props.reading?.voltages.map((value) => (value === null ? null : value * 1000)) ?? [],
);

const barKind = (group: number): 'outlier' | 'balancing' | null => {
  if (props.reading?.stats?.outliers.includes(group)) {
    return 'outlier';
  }
  return props.reading?.balancing?.active[group - 1] ? 'balancing' : null;
};
</script>

<template>
  <PanelSection
    id="cells-panel"
    title="Cell voltages"
    heading-id="cells-heading"
  >
    <PanelWarning v-if="reading?.cell_error">
      The cell voltages could not be read.
    </PanelWarning>
    <PanelWarning v-if="reading?.balancing_error">
      The cell balancing state could not be read.
    </PanelWarning>
    <p
      v-if="measuredAgo !== null"
      class="age"
    >
      Measured by the battery module {{ elapsed(measuredAgo) }} ago
    </p>
    <FactList :entries="facts" />
    <DeviationChart
      chart-id="chart"
      label="Deviation of each cell from the median voltage"
      :values="millivoltValues"
      :center="reading?.stats ? reading.stats.median * 1000 : null"
      unit="mV"
      :minimum-extent="2"
      :bar-kind="barKind"
    >
      Deviation of each cell from the median, in millivolts. Red cells are outliers; orange cells are being
      balanced now. Hover a bar for its values.
    </DeviationChart>
    <details v-if="reading">
      <summary>Show all cells as a table</summary>
      <CellTable :reading="reading" />
    </details>
  </PanelSection>
</template>

<style scoped>
.age {
  margin: 0 0 12px;
  color: var(--muted);
}
</style>
