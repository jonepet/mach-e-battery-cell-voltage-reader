<script setup lang="ts">
import { computed } from 'vue';

import { millivolts } from '../format';
import type { Reading } from '../types';
import CellTable from './CellTable.vue';
import DeviationChart from './DeviationChart.vue';
import FactList from './FactList.vue';
import PanelSection from './PanelSection.vue';
import PanelWarning from './PanelWarning.vue';

const props = defineProps<{ reading: Reading | null }>();

const facts = computed(() => {
  const reading = props.reading;
  if (!reading?.stats) {
    return [];
  }
  const { stats, voltages } = reading;
  const outliers = stats.outliers.length ? stats.outliers.map((cell) => `#${cell}`).join(', ') : 'None';
  return [
    ['Readings', `${stats.valid} / ${voltages.length}`],
    ['Minimum', `${stats.minimum.toFixed(4)} V (#${stats.min_cell})`],
    ['Maximum', `${stats.maximum.toFixed(4)} V (#${stats.max_cell})`],
    ['Mean', `${stats.mean.toFixed(4)} V`],
    ['Spread', `${millivolts(stats.spread)}${stats.spread_exceeded ? ' — above warning limit' : ''}`],
    ['Std. deviation', millivolts(stats.stdev)],
    ['Outliers', outliers],
  ] as const;
});

const millivoltValues = computed(
  () => props.reading?.voltages.map((value) => (value === null ? null : value * 1000)) ?? [],
);
const outliers = computed(() => new Set(props.reading?.stats?.outliers));
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
    <FactList :entries="facts" />
    <DeviationChart
      chart-id="chart"
      label="Deviation of each cell from the median voltage"
      :values="millivoltValues"
      :center="reading?.stats ? reading.stats.median * 1000 : null"
      unit="mV"
      :minimum-extent="2"
      :highlighted="outliers"
      highlight-class="outlier"
    >
      Deviation of each cell from the median, in millivolts. Hover a bar for its value.
    </DeviationChart>
    <details v-if="reading">
      <summary>Show all cells as a table</summary>
      <CellTable :reading="reading" />
    </details>
  </PanelSection>
</template>
