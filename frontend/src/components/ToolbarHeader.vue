<script setup lang="ts">
import { computed } from 'vue';

import { usePortControls } from '../composables/usePortControls';
import type { ConnectionStatus, MonitorState } from '../types';

const props = defineProps<{ state: MonitorState; live: boolean }>();

const { ports, selected, notice, refresh, connect, disconnect } = usePortControls();

const status = computed(() => props.state.status);
const statusText = computed(() => {
  if (!props.live) {
    return 'Reader service unreachable. Reconnecting…';
  }
  const text: Readonly<Record<ConnectionStatus, string>> = {
    disconnected: 'Disconnected',
    connecting: 'Connecting…',
    connected: 'Connected',
    failed: 'Connection failed. Check the adapter and that the vehicle is switched on, then connect again.',
    port_busy: 'The adapter is in use by another program. Close that program, then connect again.',
  };
  return notice.value ?? [text[status.value], props.state.port].filter(Boolean).join(' — ');
});
</script>

<template>
  <header class="toolbar">
    <h1>Mach-E Cell Voltages</h1>
    <form
      class="toolbar__controls"
      @submit.prevent="connect"
    >
      <label for="port">Adapter port</label>
      <select
        id="port"
        v-model="selected"
        name="port"
      >
        <option
          v-for="port in ports"
          :key="port"
          :value="port"
        >
          {{ port }}
        </option>
      </select>
      <button
        type="button"
        @click="refresh"
      >
        Refresh
      </button>
      <button
        type="submit"
        :disabled="!live || status === 'connected' || status === 'connecting' || !selected"
      >
        Connect
      </button>
      <button
        type="button"
        :disabled="!live || status !== 'connected'"
        @click="disconnect"
      >
        Disconnect
      </button>
    </form>
    <p
      class="status"
      :class="{ 'status--failed': live && (status === 'failed' || status === 'port_busy') }"
      role="status"
      aria-live="polite"
    >
      {{ statusText }}
    </p>
  </header>
</template>

<style scoped>
.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 24px;
  padding: 12px 16px;
  background: var(--panel);
  border-bottom: 1px solid var(--border);
}

h1 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.toolbar__controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.status {
  margin: 0;
  color: var(--muted);
}

.status--failed {
  color: var(--error);
}
</style>
