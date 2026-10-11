<script setup lang="ts">
import { computed } from 'vue';

import type { MonitorState } from '../types';
import FactList from './FactList.vue';
import PanelSection from './PanelSection.vue';

const props = defineProps<{ state: MonitorState }>();

const facts = computed(
  () =>
    [
      ['Port', props.state.port ?? '—'],
      ['Device', props.state.adapter?.device ?? '—'],
      ['ELM version', props.state.adapter?.elm_version ?? '—'],
      ['Adapter supply', props.state.adapter?.battery_voltage ?? '—'],
      ['Read duration', props.state.reading ?`${props.state.reading.duration_s.toFixed(1)} s` : '—'],
    ] as const,
);
</script>

<template>
  <PanelSection
    title="Adapter"
    heading-id="adapter-heading"
  >
    <FactList :entries="facts" />
  </PanelSection>
</template>
