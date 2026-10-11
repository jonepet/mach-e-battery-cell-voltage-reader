<script setup lang="ts">
import { signalValue } from '../format';
import type { SignalGroup, SignalReading } from '../types';
import PanelSection from './PanelSection.vue';

defineProps<{ title: string; group: SignalGroup; signals: readonly SignalReading[] }>();
</script>

<template>
  <PanelSection
    :title="title"
    :heading-id="`${group}-heading`"
  >
    <div
      :id="group"
      class="tiles"
    >
      <div
        v-for="signal in signals.filter((candidate) => candidate.group === group)"
        :key="signal.key"
        class="tile"
        :class="{ 'tile--error': signal.value === null }"
      >
        <span class="tile__label">{{ signal.label }}</span>
        <span class="tile__value">{{ signalValue(signal) }}</span>
      </div>
    </div>
  </PanelSection>
</template>

<style scoped>
.tiles {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 10px;
}

.tile {
  display: grid;
  gap: 4px;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.tile--error {
  border-color: var(--error);
}

.tile__label {
  color: var(--muted);
  font-size: 13px;
}

.tile__value {
  font-size: 22px;
  font-variant-numeric: tabular-nums;
}
</style>
