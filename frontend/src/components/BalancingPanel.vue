<script setup lang="ts">
import { computed } from 'vue';

import { chargePercent, duration, orDash } from '../format';
import type { Reading } from '../types';
import DeviationChart from './DeviationChart.vue';
import FactList from './FactList.vue';
import PanelSection from './PanelSection.vue';
import PanelWarning from './PanelWarning.vue';

const props = defineProps<{ reading: Reading | null }>();

const balancing = computed(() => props.reading?.balancing);

const facts = computed(() => {
  const current = balancing.value;
  if (!current) {
    return [];
  }
  const spread =
    current.charge_min === null || current.charge_max === null ? null : current.charge_max - current.charge_min;
  return [
    ['Mean state of charge', orDash(current.charge_mean, chargePercent)],
    ['Lowest', orDash(current.charge_min, chargePercent)],
    ['Highest', orDash(current.charge_max, chargePercent)],
    ['Spread', orDash(spread, (value) => `${value.toFixed(2)} % points`)],
    ['Groups balancing', `${current.active_count} / ${current.active.length}`],
    ['Longest running', current.active_count ? duration(current.longest_s) : '—'],
  ] as const;
});

const balancingGroups = computed(
  () => new Set(balancing.value?.active.flatMap((active, index) => (active ? [index + 1] : []))),
);
</script>

<template>
  <PanelSection
    title="Cell group charge and balancing"
    heading-id="balancing-heading"
  >
    <PanelWarning v-if="reading?.balancing_error">
      The cell balancing state could not be read.
    </PanelWarning>
    <FactList :entries="facts" />
    <DeviationChart
      v-if="balancing"
      chart-id="balancing-chart"
      label="State of charge of each cell group and its balancing state"
      :values="balancing.charge"
      :center="balancing.charge_mean"
      unit="%"
      :minimum-extent="0.2"
      :highlighted="balancingGroups"
      highlight-class="balancing"
    >
      State of charge of each cell group relative to the mean, in percentage points. Orange groups are being
      balanced now. Hover a bar for its value and how long it has been balancing.
    </DeviationChart>
  </PanelSection>
</template>
