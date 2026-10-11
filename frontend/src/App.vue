<script setup lang="ts">
import { computed } from 'vue';

import AdapterPanel from './components/AdapterPanel.vue';
import CellVoltagesPanel from './components/CellVoltagesPanel.vue';
import GroupHealthPanel from './components/GroupHealthPanel.vue';
import GroupReadout from './components/GroupReadout.vue';
import SignalPanel from './components/SignalPanel.vue';
import ToolbarHeader from './components/ToolbarHeader.vue';
import { provideGroupHover } from './composables/useGroupHover';
import { useMonitor } from './composables/useMonitor';

const { state, live } = useMonitor();
provideGroupHover();

const reading = computed(() => state.value.reading);
const signals = computed(() => reading.value?.signals ?? []);
</script>

<template>
  <ToolbarHeader
    :state="state"
    :live="live"
  />
  <main>
    <SignalPanel
      title="Vehicle"
      group="vehicle"
      :signals="signals"
    />
    <SignalPanel
      title="High-voltage battery"
      group="battery"
      :signals="signals"
    />
    <SignalPanel
      title="Battery temperatures"
      group="temperature"
      :signals="signals"
    />
    <CellVoltagesPanel :reading="reading" />
    <GroupHealthPanel :reading="reading" />
    <AdapterPanel :state="state" />
  </main>
  <GroupReadout :reading="reading" />
</template>

<style scoped>
main {
  display: grid;
  align-content: start;
  gap: 16px;
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
  padding: 16px;
}
</style>
